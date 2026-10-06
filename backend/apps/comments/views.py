from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from apps.reels.models import Reel
from apps.notifications.models import Notification
from .models import Comment, CommentLike
from .serializers import CommentSerializer

class ReelCommentsView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self): return Comment.objects.filter(reel_id=self.kwargs["pk"], parent__isnull=True).select_related("user").prefetch_related("replies__user", "likes")
    def perform_create(self, serializer):
        reel = get_object_or_404(Reel, pk=self.kwargs["pk"])
        parent_id = self.request.data.get("parent")
        parent = get_object_or_404(Comment, pk=parent_id, reel=reel) if parent_id else None
        comment = serializer.save(user=self.request.user, reel=reel, parent=parent)
        if reel.author_id != self.request.user.id and Notification.should_send(reel.author, "comment"):
            Notification.objects.create(recipient=reel.author, actor=self.request.user, type="comment", text=f"@{self.request.user.username}: {comment.text[:180]}")

class CommentDeleteView(generics.DestroyAPIView):
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id: raise PermissionDenied("You can only delete your own comments.")
        instance.delete()

class CommentLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        _, created = CommentLike.objects.get_or_create(user=request.user, comment=comment)
        if created and comment.user_id != request.user.id and Notification.should_send(comment.user, "like"):
            Notification.objects.create(recipient=comment.user, actor=request.user, type="like", text=f"@{request.user.username} liked your comment")
        return Response({"is_liked": True, "likes_count": comment.likes.count()})
    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        CommentLike.objects.filter(user=request.user, comment=comment).delete()
        return Response({"is_liked": False, "likes_count": comment.likes.count()})