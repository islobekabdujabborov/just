from django.db.models import Count
from rest_framework import permissions, viewsets
from config.permissions import IsOwnerOrReadOnly
from .models import Reel
from .serializers import ReelSerializer

class ReelViewSet(viewsets.ModelViewSet):
    serializer_class = ReelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ["caption", "book__title", "author__username"]
    ordering_fields = ["created_at"]
    def get_queryset(self):
        return Reel.objects.select_related("book", "book__author", "book__genre", "author").annotate(
            likes_count=Count("likes", distinct=True), comments_count=Count("comments", distinct=True), saves_count=Count("saves", distinct=True)).order_by("-created_at")
    def perform_create(self, serializer): serializer.save(author=self.request.user)