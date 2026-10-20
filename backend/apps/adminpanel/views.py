from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audiobooks.models import Audiobook, Bookmark, Chapter
from apps.audiobooks.serializers import AudiobookSerializer
from apps.books.models import Book
from apps.comments.models import Comment, CommentLike
from apps.interactions.models import Like, Save
from apps.library.models import ListeningProgress
from apps.reels.models import Reel
from apps.users.models import Subscription, User
from .file_cleanup import collect_model_files, schedule_file_cleanup
from .models import AdminAuditLog
from .permissions import IsPanelAdmin
from .serializers import (
    AdminAuditLogSerializer,
    AdminPanelUserSerializer,
    AdminPanelUserUpdateSerializer,
    PremiumGrantSerializer,
    active_subscription_queryset,
)


class AdminPanelPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100


def write_audit_log(admin, action, target_type, target_id, target_repr, details=None):
    AdminAuditLog.objects.create(
        admin=admin,
        admin_username=admin.username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_repr=str(target_repr)[:255],
        details=details or {},
    )


def book_delete_counts(book):
    reel_ids = Reel.objects.filter(book=book).values("pk")
    audiobook_ids = Audiobook.objects.filter(book=book).values("pk")
    return {
        "books": 1,
        "reels": Reel.objects.filter(book=book).count(),
        "audiobooks": Audiobook.objects.filter(book=book).count(),
        "chapters": Chapter.objects.filter(audiobook_id__in=audiobook_ids).count(),
        "comments": Comment.objects.filter(reel_id__in=reel_ids).count(),
        "likes": Like.objects.filter(Q(book=book) | Q(reel_id__in=reel_ids)).count(),
        "saves": Save.objects.filter(Q(book=book) | Q(reel_id__in=reel_ids)).count(),
        "bookmarks": Bookmark.objects.filter(audiobook_id__in=audiobook_ids).count(),
        "listening_progress": ListeningProgress.objects.filter(audiobook_id__in=audiobook_ids).count(),
        "reviews": book.reviews.count(),
    }


def user_delete_counts(user):
    owned_book_ids = Book.objects.filter(owner=user).values("pk")
    owned_audiobook_ids = Audiobook.objects.filter(
        Q(book_id__in=owned_book_ids) | Q(created_by=user)
    ).values("pk")
    return {
        "users": 1,
        "books": Book.objects.filter(owner=user).count(),
        "audiobooks": Audiobook.objects.filter(
            Q(book_id__in=owned_book_ids) | Q(created_by=user)
        ).count(),
        "chapters": Chapter.objects.filter(audiobook_id__in=owned_audiobook_ids).count(),
        "reels": Reel.objects.filter(author=user).count(),
        "reels_detached_from_owned_books": Reel.objects.filter(book_id__in=owned_book_ids)
        .exclude(author=user)
        .count(),
        "comments": Comment.objects.filter(user=user).count(),
        "comment_likes": CommentLike.objects.filter(user=user).count(),
        "likes": Like.objects.filter(user=user).count(),
        "saves": Save.objects.filter(user=user).count(),
        "bookmarks": Bookmark.objects.filter(user=user).count(),
        "listening_progress": ListeningProgress.objects.filter(user=user).count(),
        "subscriptions": Subscription.objects.filter(user=user).count(),
        "notifications": user.notifications.count(),
        "reviews": user.book_reviews.count(),
    }


def require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Bu amalni faqat superuser bajarishi mumkin.")


class AdminPanelStatsView(APIView):
    permission_classes = [IsPanelAdmin]

    def get(self, request):
        now = timezone.now()
        premium_user_ids = active_subscription_queryset().values("user_id").distinct()
        return Response({
            "users": User.objects.count(),
            "premium_users": User.objects.filter(pk__in=premium_user_ids).count(),
            "books": Book.objects.count(),
            "audiobooks": Audiobook.objects.count(),
            "reels": Reel.objects.count(),
            "new_users_7_days": User.objects.filter(
                date_joined__gte=now - timedelta(days=7)
            ).count(),
        })


class AdminPanelUserListView(generics.ListAPIView):
    permission_classes = [IsPanelAdmin]
    serializer_class = AdminPanelUserSerializer
    pagination_class = AdminPanelPagination

    def get_queryset(self):
        premium_subscriptions = active_subscription_queryset().filter(user_id=OuterRef("pk"))
        queryset = User.objects.annotate(
            is_premium=Exists(premium_subscriptions),
            premium_expires_at=Subquery(
                premium_subscriptions.order_by("-expires_at").values("expires_at")[:1]
            ),
            books_count=Count("uploaded_books", distinct=True),
            reels_count=Count("reels", distinct=True),
        ).order_by("id")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(username__icontains=query) | Q(email__icontains=query))
        premium = self.request.query_params.get("premium")
        if premium is not None:
            if premium.lower() not in {"true", "false"}:
                raise ValidationError({"premium": "Qiymat true yoki false bo'lishi kerak."})
            queryset = queryset.filter(is_premium=premium.lower() == "true")
        return queryset


class AdminPanelUserDetailView(APIView):
    permission_classes = [IsPanelAdmin]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        subscriptions = active_subscription_queryset()
        queryset = User.objects.filter(pk=user.pk).annotate(
            is_premium=Exists(subscriptions.filter(user_id=OuterRef("pk"))),
            premium_expires_at=Subquery(
                subscriptions.filter(user_id=OuterRef("pk"))
                .order_by("-expires_at")
                .values("expires_at")[:1]
            ),
            books_count=Count("uploaded_books", distinct=True),
            reels_count=Count("reels", distinct=True),
        )
        user_data = AdminPanelUserSerializer(queryset.get(), context={"request": request}).data
        history = user.subscriptions.all().values(
            "id",
            "plan",
            "status",
            "started_at",
            "expires_at",
            "canceled_at",
            "provider",
            "provider_ref",
            "admin_note",
        )
        return Response({**user_data, "subscriptions": list(history)})

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminPanelUserUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        was_active = user.is_active
        with transaction.atomic():
            for field, value in serializer.validated_data.items():
                setattr(user, field, value)
            user.save(update_fields=list(serializer.validated_data))
            if was_active != user.is_active:
                write_audit_log(
                    request.user,
                    "user_unbanned" if user.is_active else "user_banned",
                    "user",
                    user.pk,
                    user.username,
                    {"is_active": user.is_active},
                )
        return Response({
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
        })

    def delete(self, request, pk):
        require_superuser(request)
        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            raise ValidationError("O'z hisobingizni o'chira olmaysiz.")
        if user.is_superuser:
            raise ValidationError("Boshqa superuser hisobini o'chirib bo'lmaydi.")
        if request.query_params.get("confirm") != user.username:
            raise ValidationError({"confirm": "Tasdiqlash uchun foydalanuvchi nomini aynan kiriting."})

        counts = user_delete_counts(user)
        user_id, username = user.pk, user.username
        owned_books = Book.objects.filter(owner=user)
        audiobooks = Audiobook.objects.filter(Q(book__owner=user) | Q(created_by=user)).distinct()
        chapters = Chapter.objects.filter(audiobook__in=audiobooks)
        cleanup_files = [(user.avatar.storage, user.avatar.name)] if user.avatar else []
        cleanup_files.extend(collect_model_files(owned_books, ["cover"]))
        cleanup_files.extend(collect_model_files(audiobooks, ["audio_file"]))
        cleanup_files.extend(collect_model_files(chapters, ["audio_file"]))
        try:
            with transaction.atomic():
                write_audit_log(request.user, "user_deleted", "user", user_id, username, counts)
                owned_books.delete()
                Audiobook.objects.filter(created_by=user).exclude(book__owner=user).delete()
                user.delete()
                schedule_file_cleanup(cleanup_files)
        except ProtectedError as exc:
            raise ValidationError(
                "Foydalanuvchiga tegishli ayrim ma'lumotlar sabab hisobni o'chirib bo'lmadi."
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPanelUserDeletePreviewView(APIView):
    permission_classes = [IsPanelAdmin]

    def get(self, request, pk):
        require_superuser(request)
        user = get_object_or_404(User, pk=pk)
        return Response({"username": user.username, "will_delete": user_delete_counts(user)})


class AdminPanelPremiumView(APIView):
    permission_classes = [IsPanelAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = PremiumGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data["plan"]
        duration_days = {
            Subscription.PLAN_MONTHLY: 30,
            Subscription.PLAN_YEARLY: 365,
            Subscription.PLAN_CUSTOM: serializer.validated_data.get("days"),
        }[plan]
        now = timezone.now()
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().filter(
                user=user,
                status=Subscription.STATUS_ACTIVE,
                expires_at__gt=now,
            ).first()
            if subscription:
                subscription.expires_at += timedelta(days=duration_days)
                subscription.plan = plan
                subscription.provider = "manual"
                subscription.provider_ref = request.user.username
                subscription.admin_note = serializer.validated_data.get("note", "")
                subscription.save(update_fields=[
                    "expires_at", "plan", "provider", "provider_ref", "admin_note",
                ])
            else:
                subscription = Subscription.objects.create(
                    user=user,
                    plan=plan,
                    status=Subscription.STATUS_ACTIVE,
                    started_at=now,
                    expires_at=now + timedelta(days=duration_days),
                    provider="manual",
                    provider_ref=request.user.username,
                    admin_note=serializer.validated_data.get("note", ""),
                )
            write_audit_log(
                request.user,
                "premium_granted",
                "user",
                user.pk,
                user.username,
                {
                    "plan": plan,
                    "days": duration_days,
                    "expires_at": subscription.expires_at.isoformat(),
                    "note": subscription.admin_note,
                },
            )
        return Response(self._serialize(subscription))

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        now = timezone.now()
        subscription = active_subscription_queryset().filter(user=user).order_by("-expires_at").first()
        if not subscription:
            return Response({"detail": "Faol Premium obuna topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            subscription.status = Subscription.STATUS_CANCELED
            subscription.expires_at = now
            subscription.canceled_at = now
            subscription.save(update_fields=["status", "expires_at", "canceled_at"])
            write_audit_log(
                request.user,
                "premium_revoked",
                "user",
                user.pk,
                user.username,
                {"subscription_id": subscription.pk},
            )
        return Response(self._serialize(subscription))

    @staticmethod
    def _serialize(subscription):
        return {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "started_at": subscription.started_at,
            "expires_at": subscription.expires_at,
            "provider": subscription.provider,
            "provider_ref": subscription.provider_ref,
            "admin_note": subscription.admin_note,
        }


class AdminPanelBookListView(generics.ListAPIView):
    permission_classes = [IsPanelAdmin]
    pagination_class = AdminPanelPagination

    def get_queryset(self):
        queryset = Book.objects.select_related("author", "owner", "genre").prefetch_related(
            "audiobooks__chapters"
        ).annotate(reels_count=Count("reels", distinct=True)).order_by("-created_at")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(author__name__icontains=query)
                | Q(owner__username__icontains=query)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        results = []
        for book in page:
            audiobook = next(iter(book.audiobooks.all()), None)
            chapters = list(audiobook.chapters.all()) if audiobook else []
            results.append({
                "id": book.id,
                "title": book.title,
                "author": book.author.name,
                "owner": book.owner.username if book.owner else None,
                "has_audio": bool(audiobook and (audiobook.audio_file or chapters)),
                "audiobook_id": audiobook.id if audiobook else None,
                "access": audiobook.access if audiobook else None,
                "reels_count": book.reels_count,
                "created_at": book.created_at,
            })
        return self.get_paginated_response(results)


class AdminPanelBookDeletePreviewView(APIView):
    permission_classes = [IsPanelAdmin]

    def get(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        return Response({"title": book.title, "will_delete": book_delete_counts(book)})


class AdminPanelBookDeleteView(APIView):
    permission_classes = [IsPanelAdmin]

    def delete(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        counts = book_delete_counts(book)
        audiobooks = Audiobook.objects.filter(book=book)
        chapters = Chapter.objects.filter(audiobook__in=audiobooks)
        files = collect_model_files(Book.objects.filter(pk=book.pk), ["cover"])
        files.extend(collect_model_files(audiobooks, ["audio_file"]))
        files.extend(collect_model_files(chapters, ["audio_file"]))
        try:
            with transaction.atomic():
                write_audit_log(request.user, "book_deleted", "book", book.pk, book.title, counts)
                Reel.objects.filter(book=book).delete()
                book.delete()
                schedule_file_cleanup(files)
        except ProtectedError as exc:
            raise ValidationError("Kitobga bog'langan ma'lumotlar sabab uni o'chirib bo'lmadi.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPanelAudiobookAccessView(APIView):
    permission_classes = [IsPanelAdmin]

    def patch(self, request, pk):
        audiobook = get_object_or_404(
            Audiobook.objects.select_related("book"),
            pk=pk,
        )
        access = request.data.get("access")
        if access not in {Audiobook.ACCESS_FREE, Audiobook.ACCESS_PREMIUM}:
            raise ValidationError({"access": "Qiymat free yoki premium bo'lishi kerak."})
        old_access = audiobook.access
        with transaction.atomic():
            audiobook.access = access
            audiobook.save(update_fields=["access"])
            if old_access != access:
                write_audit_log(
                    request.user,
                    "audiobook_access_changed",
                    "audiobook",
                    audiobook.pk,
                    audiobook.book.title,
                    {"from": old_access, "to": access},
                )
        return Response(AudiobookSerializer(audiobook, context={"request": request}).data)


class AdminPanelReelListView(generics.ListAPIView):
    permission_classes = [IsPanelAdmin]
    pagination_class = AdminPanelPagination

    def get_queryset(self):
        queryset = Reel.objects.select_related(
            "author", "book", "book__author", "book__genre"
        ).annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count("comments", distinct=True),
        ).order_by("-created_at")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(caption__icontains=query)
                | Q(author__username__icontains=query)
                | Q(book__title__icontains=query)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        data = [{
            "id": reel.id,
            "video": request.build_absolute_uri(reel.video.url) if reel.video else None,
            "caption": reel.caption,
            "author": {"id": reel.author_id, "username": reel.author.username},
            "book": {"id": reel.book_id, "title": reel.book.title} if reel.book_id else None,
            "created_at": reel.created_at,
            "likes_count": reel.likes_count,
            "comments_count": reel.comments_count,
        } for reel in page]
        return self.get_paginated_response(data)


class AdminPanelReelDeletePreviewView(APIView):
    permission_classes = [IsPanelAdmin]

    def get(self, request, pk):
        reel = get_object_or_404(Reel, pk=pk)
        return Response({"caption": reel.caption, "will_delete": self._counts(reel)})

    @staticmethod
    def _counts(reel):
        return {
            "reels": 1,
            "comments": reel.comments.count(),
            "likes": reel.likes.count(),
            "saves": reel.saves.count(),
        }


class AdminPanelReelDeleteView(APIView):
    permission_classes = [IsPanelAdmin]

    def delete(self, request, pk):
        reel = get_object_or_404(Reel, pk=pk)
        counts = AdminPanelReelDeletePreviewView._counts(reel)
        with transaction.atomic():
            write_audit_log(request.user, "reel_deleted", "reel", reel.pk, reel.caption, counts)
            reel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPanelAuditLogView(generics.ListAPIView):
    permission_classes = [IsPanelAdmin]
    pagination_class = AdminPanelPagination
    serializer_class = AdminAuditLogSerializer

    def get_queryset(self):
        return AdminAuditLog.objects.select_related("admin").all()
