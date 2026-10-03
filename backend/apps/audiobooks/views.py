from django.shortcuts import get_object_or_404
import math
from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from config.permissions import IsOwnerOrReadOnly
from .models import Audiobook, Chapter
from .serializers import AudiobookSerializer, ChapterSerializer
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