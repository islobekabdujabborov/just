from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, viewsets
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
    def perform_create(self, serializer): serializer.save(audiobook=get_object_or_404(Audiobook, pk=self.kwargs["pk"]))

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
        progress, _ = ListeningProgress.objects.update_or_create(user=request.user, audiobook=audiobook, defaults={
            "chapter": chapter, "position": max(0, int(request.data.get("position", 0))), "percentage": min(100, max(0, float(request.data.get("percentage", 0))))})
        return Response({"position": progress.position, "percentage": progress.percentage, "chapter": progress.chapter_id})