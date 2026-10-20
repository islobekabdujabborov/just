import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audiobooks.models import Audiobook, Chapter, validate_audio
from apps.books.models import Author, Book, Genre, validate_cover
from config.permissions import IsOwnerOrReadOnly
from apps.users.models import Follow
from .models import Reel
from .serializers import ReelSerializer


def _ffprobe_duration(upload, expected_stream):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0
    suffix = Path(upload.name).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        upload.seek(0)
        for chunk in upload.chunks():
            temp_file.write(chunk)
        temp_file.flush()
        upload.seek(0)
        try:
            result = subprocess.run(
                [
                    ffprobe, "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type", "-of", "json", temp_file.name,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValidationError("Yuklangan media faylni tekshirib bo'lmadi.") from exc
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError("Yuklangan media fayl formati noto'g'ri.") from exc
    if expected_stream not in {stream.get("codec_type") for stream in metadata.get("streams", [])}:
        raise ValidationError("Audio fayl ichida audio oqimi topilmadi.")
    try:
        return max(0, int(float(metadata.get("format", {}).get("duration", 0))))
    except (TypeError, ValueError):
        return 0


def _get_reel_queryset():
    chapters = Chapter.objects.order_by("order")
    audiobooks = Audiobook.objects.prefetch_related(
        Prefetch("chapters", queryset=chapters, to_attr="reel_chapters")
    )
    return Reel.objects.select_related(
        "book", "book__author", "book__genre", "author"
    ).prefetch_related(
        Prefetch("book__audiobooks", queryset=audiobooks, to_attr="reel_audiobooks")
    ).annotate(
        likes_count=Count("likes", distinct=True),
        comments_count=Count("comments", distinct=True),
        saves_count=Count("saves", distinct=True),
    ).order_by("-created_at")


class ReelViewSet(viewsets.ModelViewSet):
    serializer_class = ReelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ["caption", "book__title", "author__username"]
    ordering_fields = ["created_at"]
    def get_queryset(self):
        return _get_reel_queryset()
    def perform_create(self, serializer): serializer.save(author=self.request.user)


class ReelComposeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        video = request.FILES.get("video")
        if not video:
            raise ValidationError({"video": "Reel uchun video tanlang."})
        if Path(video.name).suffix.lower() not in {".mp4", ".mov", ".webm"}:
            raise ValidationError({"video": "Video MP4, MOV yoki WebM bo'lishi kerak."})
        if not video.size or video.size > 100 * 1024 * 1024:
            raise ValidationError({"video": "Video bo'sh bo'lmasligi va 100 MB dan oshmasligi kerak."})
        if len(request.data.get("caption", "")) > 500:
            raise ValidationError({"caption": "Reel izohi 500 belgidan oshmasligi kerak."})

        book_id = request.data.get("book_id")
        audio_files = request.FILES.getlist("audio_files")
        if len(audio_files) > 30:
            raise ValidationError({"audio_files": "Bir martada ko'pi bilan 30 ta bob yuklash mumkin."})
        if book_id and any(key in request.data for key in ("title", "author_name", "genre")):
            raise ValidationError("Mavjud kitobni tanlang yoki yangi kitob ma'lumotlarini kiriting.")

        durations = []
        for audio in audio_files:
            if Path(audio.name).suffix.lower() not in {".mp3", ".m4a", ".wav", ".ogg"}:
                raise ValidationError({"audio_files": "Audio MP3, M4A, WAV yoki OGG bo'lishi kerak."})
            if not audio.size:
                raise ValidationError({"audio_files": "Audio fayl bo'sh bo'lmasligi kerak."})
            try:
                validate_audio(audio)
            except DjangoValidationError as exc:
                raise ValidationError({"audio_files": exc.messages}) from exc
            durations.append(_ffprobe_duration(audio, "audio"))

        chapter_titles = request.data.getlist("chapter_titles")
        preview_orders = [
            order.strip()
            for value in request.data.getlist("free_preview_orders")
            for order in value.split(",")
            if order.strip()
        ]
        preview_flags = request.data.getlist("chapter_free_preview")
        if chapter_titles and len(chapter_titles) != len(audio_files):
            raise ValidationError({"chapter_titles": "Har bir audio fayl uchun alohida bob nomini kiriting."})
        free_preview = set()
        for order in preview_orders:
            try:
                preview_order = int(order)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"free_preview_orders": "Bepul namuna boblari tartibi noto'g'ri."}) from exc
            if not 1 <= preview_order <= len(audio_files):
                raise ValidationError({"free_preview_orders": "Bepul namuna boblari tartibi noto'g'ri."})
            free_preview.add(preview_order)
        for index, flag in enumerate(preview_flags, start=1):
            if str(flag).lower() in {"1", "true", "yes", "on"}:
                free_preview.add(index)
        if len(preview_flags) > len(audio_files):
            raise ValidationError({"chapter_free_preview": "Har bir audio fayl uchun alohida namuna belgilang."})
        if any(len(title.strip()) > 200 for title in chapter_titles):
            raise ValidationError({"chapter_titles": "Bob nomi 200 belgidan oshmasligi kerak."})

        access = request.data.get("access", Audiobook.ACCESS_FREE)
        if access not in {Audiobook.ACCESS_FREE, Audiobook.ACCESS_PREMIUM}:
            raise ValidationError({"access": "Audio turi Ochiq yoki Premium bo'lishi kerak."})

        saved_files = []
        try:
            with transaction.atomic():
                if book_id:
                    book = get_object_or_404(Book.objects.select_related("owner"), pk=book_id)
                    existing_audiobook = Audiobook.objects.filter(book=book).prefetch_related("chapters").first()
                    can_reuse = (
                        book.owner_id == request.user.id
                        or request.user.is_staff
                        or (book.owner_id is None and existing_audiobook is None)
                    )
                    if not can_reuse:
                        raise ValidationError({"book_id": "Bu kitobni reelga biriktirish huquqingiz yo'q."})
                else:
                    title = (request.data.get("title") or "").strip()
                    author_name = (request.data.get("author_name") or "").strip()
                    genre_name = (request.data.get("genre") or "").strip()
                    if not title or not author_name or not genre_name:
                        raise ValidationError("Kitob nomi, muallifi va janrini kiriting.")
                    if len(title) > 240 or len(author_name) > 180:
                        raise ValidationError("Kitob nomi 240, muallif nomi 180 belgidan oshmasligi kerak.")
                    language = request.data.get("language", "uz")
                    if len(language) > 12:
                        raise ValidationError({"language": "Kitob tili 12 belgidan oshmasligi kerak."})
                    genre = get_object_or_404(Genre, name=genre_name)
                    author, _ = Author.objects.get_or_create(name=author_name)
                    book = Book(
                        title=title,
                        author=author,
                        genre=genre,
                        description=request.data.get("description", ""),
                        language=language,
                        owner=request.user,
                    )
                    cover = request.FILES.get("cover")
                    if cover:
                        if not cover.size:
                            raise ValidationError({"cover": "Muqova fayli bo'sh bo'lmasligi kerak."})
                        try:
                            validate_cover(cover)
                        except DjangoValidationError as exc:
                            raise ValidationError({"cover": exc.messages}) from exc
                        if Path(cover.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                            raise ValidationError({"cover": "Muqova JPG, PNG yoki WebP bo'lishi kerak."})
                        book.cover.save(cover.name, cover, save=False)
                        saved_files.append((book.cover.storage, book.cover.name))
                    book.save()

                audiobook = Audiobook.objects.filter(book=book).prefetch_related("chapters").first()
                if audio_files:
                    if audiobook and audiobook.created_by_id != request.user.id:
                        raise ValidationError({"audio_files": "Bu kitobning audiokitobini tahrirlash huquqingiz yo'q."})
                    if audiobook is None:
                        audiobook = Audiobook.objects.create(
                            book=book,
                            created_by=request.user,
                            access=access,
                        )
                    else:
                        audiobook.access = access
                        audiobook.save(update_fields=["access"])
                    if book.owner_id is None:
                        book.owner = request.user
                        book.save(update_fields=["owner"])

                    next_order = (audiobook.chapters.order_by("-order").values_list("order", flat=True).first() or 0) + 1
                    for index, audio in enumerate(audio_files):
                        title = chapter_titles[index].strip() if index < len(chapter_titles) else ""
                        if not title:
                            title = f"{next_order + index}-bob"
                        chapter = Chapter(
                            audiobook=audiobook,
                            title=title,
                            duration=durations[index],
                            order=next_order + index,
                            is_free_preview=index + 1 in free_preview,
                        )
                        chapter.audio_file.save(audio.name, audio, save=False)
                        saved_files.append((chapter.audio_file.storage, chapter.audio_file.name))
                        chapter.save()
                    audiobook.duration = (audiobook.duration or 0) + sum(durations)
                    audiobook.save(update_fields=["duration"])
                    book.duration = (book.duration or 0) + sum(durations)
                    book.save(update_fields=["duration"])

                reel = Reel(
                    caption=request.data.get("caption", ""),
                    book=book,
                    author=request.user,
                )
                reel.video.save(video.name, video, save=False)
                saved_files.append((reel.video.storage, reel.video.name))
                reel.save()
                reel = _get_reel_queryset().get(pk=reel.pk)
                response_data = ReelSerializer(reel, context={"request": request}).data
        except Exception:
            for storage, name in saved_files:
                storage.delete(name)
            raise
        return Response(response_data, status=status.HTTP_201_CREATED)


class FollowingReelFeedView(generics.ListAPIView):
    serializer_class = ReelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        followed_users = Follow.objects.filter(follower=self.request.user).values("followed_id")
        return _get_reel_queryset().filter(author_id__in=followed_users)