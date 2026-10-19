from django.shortcuts import get_object_or_404
import math
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from config.permissions import IsOwnerOrReadOnly
from .models import Audiobook, Bookmark, Chapter
from .serializers import AudiobookSerializer, BookmarkSerializer, ChapterSerializer
from .access import can_access_audiobook, can_access_chapter, signed_audio_url
from apps.library.models import ListeningProgress

class AudiobookViewSet(viewsets.ModelViewSet):
    serializer_class = AudiobookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self): return Audiobook.objects.select_related("book", "book__author", "book__genre").prefetch_related("chapters")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(created_by=self.request.user)
    def perform_update(self, serializer):
        if serializer.instance.created_by_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit audiobooks you uploaded.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.created_by_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete audiobooks you uploaded.")
        instance.delete()

class ChapterListView(generics.ListCreateAPIView):
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self): return Chapter.objects.filter(audiobook_id=self.kwargs["pk"]).order_by("order")
    def perform_create(self, serializer):
        audiobook = get_object_or_404(Audiobook, pk=self.kwargs["pk"])
        if audiobook.created_by_id != self.request.user.id and audiobook.book.owner_id != self.request.user.id:
            raise PermissionDenied("You can only add chapters to audiobooks you uploaded.")
        serializer.save(audiobook=audiobook)

class ChapterDetailView(generics.RetrieveAPIView):
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Chapter.objects.select_related("audiobook", "audiobook__book")

class ChapterStreamView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        chapter = get_object_or_404(Chapter.objects.select_related("audiobook"), pk=pk)
        if not chapter.audio_file:
            return Response({"detail": "Bob uchun audio mavjud emas."}, status=status.HTTP_404_NOT_FOUND)
        if not can_access_chapter(request.user, chapter):
            return Response({"detail": "Bu bob uchun Premium obuna kerak."}, status=status.HTTP_403_FORBIDDEN)
        return Response({"url": signed_audio_url(request, "chapter", chapter)})

class AudiobookStreamView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        audiobook = get_object_or_404(Audiobook, pk=pk)
        if not audiobook.audio_file:
            return Response({"detail": "Audiokitob uchun audio mavjud emas."}, status=status.HTTP_404_NOT_FOUND)
        if not can_access_audiobook(request.user, audiobook):
            return Response({"detail": "Bu audiokitob uchun Premium obuna kerak."}, status=status.HTTP_403_FORBIDDEN)
        return Response({"url": signed_audio_url(request, "audiobook", audiobook)})

class ProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, pk):
        progress = ListeningProgress.objects.filter(user=request.user, audiobook_id=pk).select_related("chapter").first()
        if not progress: return Response({"position": 0, "percentage": 0, "chapter": None})
        return Response({"position": progress.position, "percentage": progress.percentage, "chapter": progress.chapter_id, "updated_at": progress.updated_at})
    def post(self, request, pk):
        audiobook = get_object_or_404(Audiobook, pk=pk)
        chapter_id = request.data.get("chapter")
        chapter = get_object_or_404(Chapter, pk=chapter_id, audiobook=audiobook) if chapter_id else None
        try:
            position = int(request.data.get("position", 0))
            percentage = float(request.data.get("percentage", 0))
        except (TypeError, ValueError):
            return Response({"detail": "Position and percentage must be numeric."}, status=400)
        if position < 0 or not math.isfinite(percentage) or not 0 <= percentage <= 100:
            return Response({"detail": "Position must be non-negative and percentage must be between 0 and 100."}, status=400)
        progress, _ = ListeningProgress.objects.update_or_create(user=request.user, audiobook=audiobook, defaults={
            "chapter": chapter, "position": position, "percentage": percentage})
        return Response({"position": progress.position, "percentage": progress.percentage, "chapter": progress.chapter_id})

class AudiobookBookmarkListView(generics.ListCreateAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_audiobook(self):
        if not hasattr(self, "_audiobook"):
            self._audiobook = get_object_or_404(Audiobook, pk=self.kwargs["pk"])
        return self._audiobook

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user, audiobook=self.get_audiobook()).select_related("chapter")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["audiobook"] = self.get_audiobook()
        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, audiobook=self.get_audiobook())

class BookmarkDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_object(self, pk):
        bookmark = get_object_or_404(Bookmark.objects.select_related("audiobook", "chapter"), pk=pk)
        self.check_object_permissions(self.request, bookmark)
        return bookmark

    def patch(self, request, pk):
        bookmark = self.get_object(pk)
        serializer = BookmarkSerializer(bookmark, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        bookmark = self.get_object(pk)
        bookmark.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)