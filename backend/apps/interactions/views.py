from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.books.models import Book
from apps.reels.models import Reel
from apps.notifications.models import Notification
from .models import Like, Save

class InteractionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    model = None
    target_model = None
    target_field = None
    result_key = "is_liked"
    notification_type = None
    def target(self, pk): return get_object_or_404(self.target_model, pk=pk)
    def count(self, obj): return self.model.objects.filter(**{self.target_field: obj}).count()
    def post(self, request, pk):
        obj = self.target(pk)
        _, created = self.model.objects.get_or_create(user=request.user, **{self.target_field: obj})
        owner = getattr(obj, "author", None)
        if created and self.notification_type and owner and owner.id != request.user.id and Notification.should_send(owner, self.notification_type):
            Notification.objects.create(recipient=owner, actor=request.user, type=self.notification_type, text=f"@{request.user.username} {self.notification_type}d your post")
        return Response({self.result_key: True, "likes_count" if self.result_key == "is_liked" else "saves_count": self.count(obj)})
    def delete(self, request, pk):
        obj = self.target(pk)
        self.model.objects.filter(user=request.user, **{self.target_field: obj}).delete()
        return Response({self.result_key: False, "likes_count" if self.result_key == "is_liked" else "saves_count": self.count(obj)})

class ReelLikeView(InteractionView):
    model, target_model, target_field, result_key, notification_type = Like, Reel, "reel", "is_liked", "like"
class ReelSaveView(InteractionView):
    model, target_model, target_field, result_key, notification_type = Save, Reel, "reel", "is_saved", "save"
class BookLikeView(InteractionView):
    model, target_model, target_field, result_key, notification_type = Like, Book, "book", "is_liked", None
class BookSaveView(InteractionView):
    model, target_model, target_field, result_key, notification_type = Save, Book, "book", "is_saved", None