from rest_framework import serializers
from apps.users.serializers import UserSerializer
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()
    class Meta: model = Notification; fields = ["id", "actor", "type", "text", "is_read", "created_at", "time_ago"]
    def get_time_ago(self, obj):
        from django.utils.timesince import timesince
        return timesince(obj.created_at).split(",")[0]