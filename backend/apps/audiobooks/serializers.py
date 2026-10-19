from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from apps.books.serializers import BookSerializer
from .models import Audiobook, Bookmark, Chapter, validate_audio
from .access import can_access_chapter

class ChapterSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    audio_file = serializers.FileField(required=False, validators=[validate_audio, FileExtensionValidator(["mp3", "m4a", "wav", "ogg"])])
    locked = serializers.SerializerMethodField()
    has_audio = serializers.SerializerMethodField()
    class Meta: model = Chapter; fields = ["id", "title", "audio_file", "audio_url", "duration", "order", "is_free_preview", "locked", "has_audio"]
    def get_locked(self, obj):
        request = self.context.get("request")
        return not can_access_chapter(request.user if request else None, obj)
    def get_audio_url(self, obj):
        if not obj.audio_file or obj.audiobook.access == Audiobook.ACCESS_PREMIUM:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.audio_file.url) if obj.audio_file and request else (obj.audio_file.url if obj.audio_file else None)
    def get_has_audio(self, obj):
        request = self.context.get("request")
        return bool(obj.audio_file and can_access_chapter(request.user if request else None, obj))
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.audiobook.access == Audiobook.ACCESS_PREMIUM:
            data["audio_file"] = None
            data["audio_url"] = None
        return data

class AudiobookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(source="book", queryset=__import__("apps.books.models", fromlist=["Book"]).Book.objects.all(), write_only=True, required=False)
    audio_file = serializers.FileField(required=False, validators=[validate_audio, FileExtensionValidator(["mp3", "m4a", "wav", "ogg"])])
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    audio_url = serializers.SerializerMethodField()
    has_audio = serializers.SerializerMethodField()
    chapters = ChapterSerializer(many=True, read_only=True)
    class Meta: model = Audiobook; fields = ["id", "book", "book_id", "created_by", "audio_file", "audio_url", "duration", "access", "has_audio", "chapters"]
    def get_audio_url(self, obj):
        if not obj.audio_file or obj.access == Audiobook.ACCESS_PREMIUM:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.audio_file.url) if obj.audio_file and request else (obj.audio_file.url if obj.audio_file else None)
    def get_has_audio(self, obj):
        return bool(obj.audio_file)
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.access == Audiobook.ACCESS_PREMIUM:
            data["audio_file"] = None
            data["audio_url"] = None
        return data

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ["id", "audiobook", "chapter", "position", "note", "created_at"]
        read_only_fields = ["id", "audiobook", "created_at"]

    def validate(self, attrs):
        chapter = attrs.get("chapter", self.instance.chapter if self.instance else None)
        audiobook = self.context.get("audiobook") or (self.instance.audiobook if self.instance else None)
        if chapter and audiobook and chapter.audiobook_id != audiobook.id:
            raise serializers.ValidationError({"chapter": "Bob ushbu audiokitobga tegishli emas."})
        return attrs