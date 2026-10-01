from rest_framework import serializers
from apps.books.serializers import BookSerializer
from .models import Audiobook, Chapter

class ChapterSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    class Meta: model = Chapter; fields = ["id", "title", "audio_file", "audio_url", "duration", "order"]
    def get_audio_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.audio_file.url) if obj.audio_file and request else (obj.audio_file.url if obj.audio_file else None)

class AudiobookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(source="book", queryset=__import__("apps.books.models", fromlist=["Book"]).Book.objects.all(), write_only=True, required=False)
    audio_url = serializers.SerializerMethodField()
    chapters = ChapterSerializer(many=True, read_only=True)
    class Meta: model = Audiobook; fields = ["id", "book", "book_id", "audio_file", "audio_url", "duration", "chapters"]
    def get_audio_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.audio_file.url) if obj.audio_file and request else (obj.audio_file.url if obj.audio_file else None)