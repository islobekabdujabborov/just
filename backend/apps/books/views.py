from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from config.permissions import IsOwnerOrReadOnly
from apps.notifications.models import Notification
from apps.interactions.models import Like, Save
from apps.library.models import ListeningProgress
from .models import Author, Book, Genre, Review
from .serializers import AuthorSerializer, BookSerializer, GenreSerializer, ReviewSerializer

class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author__name", "description", "genre__name"]
    ordering_fields = ["created_at", "rating", "title"]
    filterset_fields = ["genre__slug", "language", "author"]
    def get_queryset(self):
        return Book.objects.select_related("author", "genre", "owner").annotate(likes_count=Count("likes", distinct=True)).order_by("-created_at")
    def perform_create(self, serializer): serializer.save(owner=self.request.user)
    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit books you uploaded.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete books you uploaded.")
        instance.delete()

def update_book_rating(book_id):
    average = Review.objects.filter(book_id=book_id).aggregate(value=Avg("rating"))["value"]
    rating = Decimal(average or 0).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    Book.objects.filter(pk=book_id).update(rating=rating)

class BookReviewListView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_book(self):
        if not hasattr(self, "_book"):
            self._book = get_object_or_404(Book, pk=self.kwargs["pk"])
        return self._book

    def get_queryset(self):
        return Review.objects.filter(book=self.get_book()).select_related("user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["book"] = self.get_book()
        return context

    def perform_create(self, serializer):
        book = self.get_book()
        with transaction.atomic():
            review = serializer.save(user=self.request.user, book=book)
            update_book_rating(book.id)
            owner = book.owner
            if owner and owner.id != self.request.user.id and Notification.should_send(owner, "review"):
                Notification.objects.create(
                    recipient=owner,
                    actor=self.request.user,
                    type="review",
                    text=f"@{self.request.user.username} kitobingizga yangi baho berdi.",
                )

class ReviewDetailView(generics.GenericAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    http_method_names = ["patch", "delete", "options"]

    def get_queryset(self):
        return Review.objects.select_related("user", "book")

    def patch(self, request, *args, **kwargs):
        review = self.get_object()
        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            review = serializer.save()
            update_book_rating(review.book_id)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        review = self.get_object()
        book_id = review.book_id
        with transaction.atomic():
            review.delete()
            update_book_rating(book_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

class RecommendationsView(generics.ListAPIView):
    serializer_class = BookSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        listened_book_ids = set()
        genre_scores = {}

        if user.is_authenticated:
            listened_book_ids = set(
                ListeningProgress.objects.filter(user=user).values_list("audiobook__book_id", flat=True)
            )
            genre_sources = (
                (Like.objects.filter(user=user, book__isnull=False).values_list("book__genre_id", flat=True), 3),
                (Save.objects.filter(user=user, book__isnull=False).values_list("book__genre_id", flat=True), 2),
                (ListeningProgress.objects.filter(user=user).values_list("audiobook__book__genre_id", flat=True), 1),
            )
            for genre_ids, weight in genre_sources:
                for genre_id in genre_ids:
                    genre_scores[genre_id] = genre_scores.get(genre_id, 0) + weight

        books = Book.objects.select_related("author", "genre").annotate(
            likes_count=Count("likes", distinct=True)
        )
        if listened_book_ids:
            books = books.exclude(id__in=listened_book_ids)
        if not genre_scores:
            return books.order_by("-rating", "-likes_count", "-created_at")

        genre_score = Case(
            *[
                When(genre_id=genre_id, then=Value(score))
                for genre_id, score in genre_scores.items()
            ],
            default=Value(0),
            output_field=IntegerField(),
        )
        return books.annotate(recommendation_score=genre_score).order_by(
            "-recommendation_score", "-rating", "-likes_count", "-created_at"
        )

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_view(request):
    query = request.query_params.get("q", "").strip()
    books = Book.objects.select_related("author", "genre").annotate(likes_count=Count("likes", distinct=True)).filter(Q(title__icontains=query) | Q(author__name__icontains=query) | Q(genre__name__icontains=query)) if query else Book.objects.none()
    authors = Author.objects.filter(name__icontains=query) if query else Author.objects.none()
    users = __import__("apps.users.models", fromlist=["User"]).User.objects.filter(username__icontains=query) if query else []
    genres = Genre.objects.filter(name__icontains=query) if query else Genre.objects.none()
    reels = __import__("apps.reels.models", fromlist=["Reel"]).Reel.objects.select_related("book", "author").filter(Q(caption__icontains=query) | Q(book__title__icontains=query)) if query else []
    from apps.reels.serializers import ReelSerializer
    return Response({"books": BookSerializer(books[:20], many=True, context={"request": request}).data,
                     "authors": AuthorSerializer(authors[:20], many=True).data,
                     "users": [{"id": u.id, "username": u.username, "avatar": request.build_absolute_uri(u.avatar.url) if u.avatar else None} for u in users[:20]],
                     "genres": GenreSerializer(genres[:20], many=True).data,
                     "reels": ReelSerializer(reels[:20], many=True, context={"request": request}).data})

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def explore_view(request):
    base = Book.objects.select_related("author", "genre").annotate(likes_count=Count("likes", distinct=True))
    from apps.reels.models import Reel
    from apps.reels.serializers import ReelSerializer
    return Response({"trending": BookSerializer(base.order_by("-likes_count", "-rating")[:10], many=True, context={"request": request}).data,
                     "popular": BookSerializer(base.order_by("-rating", "-likes_count")[:10], many=True, context={"request": request}).data,
                     "new": BookSerializer(base.order_by("-created_at")[:10], many=True, context={"request": request}).data,
                     "reels": ReelSerializer(Reel.objects.select_related("book", "book__author", "book__genre", "author").annotate(likes_count=Count("likes"), comments_count=Count("comments"), saves_count=Count("saves"))[:10], many=True, context={"request": request}).data,
                     "genres": GenreSerializer(Genre.objects.all(), many=True).data})