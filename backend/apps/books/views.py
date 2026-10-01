from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from config.permissions import IsOwnerOrReadOnly
from .models import Author, Book, Genre
from .serializers import AuthorSerializer, BookSerializer, GenreSerializer

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