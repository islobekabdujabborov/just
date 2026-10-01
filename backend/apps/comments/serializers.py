from rest_framework import serializers
from apps.users.serializers import UserSerializer
from .models import Comment

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    class Meta:
        model = Comment
        fields = ["id", "user", "reel", "text", "parent", "created_at", "replies", "likes_count"]
        read_only_fields = ["id", "user", "reel", "created_at"]
    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all(), many=True, context=self.context).data