from rest_framework import serializers
from apps.books.serializers import BookSerializer
from apps.audiobooks.access import can_access_audiobook
from apps.audiobooks.models import Audiobook
from .models import Reel

class ReelSerializer(serializers.ModelSerializer):
    book = serializers.SerializerMethodField()
    book_id = serializers.PrimaryKeyRelatedField(source="book", queryset=__import__("apps.books.models", fromlist=["Book"]).Book.objects.all(), write_only=True, required=False, allow_null=True)
    author = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    saves_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    t = serializers.CharField(source="book.title", read_only=True, default="")
    a = serializers.CharField(source="book.author.name", read_only=True, default="")
    g = serializers.CharField(source="book.genre.name", read_only=True, default="")
    d = serializers.CharField(source="book.duration", read_only=True, default="")
    u = serializers.CharField(source="author.username", read_only=True)
    cap = serializers.CharField(source="caption", read_only=True)
    class Meta:
        model = Reel
        fields = ["id", "video", "video_url", "caption", "book", "book_id", "author", "created_at", "likes_count", "comments_count", "saves_count", "is_liked", "is_saved", "t", "a", "g", "d", "u", "cap"]
        read_only_fields = ["author", "created_at", "likes_count", "comments_count", "saves_count", "is_liked", "is_saved"]
    def _url(self, obj, field):
        file = getattr(obj, field)
        request = self.context.get("request")
        return request.build_absolute_uri(file.url) if file and request else (file.url if file else None)
    def get_video_url(self, obj): return self._url(obj, "video")
    def get_book(self, obj):
        if not obj.book_id:
            return None
        data = BookSerializer(obj.book, context=self.context).data
        audiobook = next(iter(getattr(obj.book, "reel_audiobooks", [])), None)
        chapters = audiobook.reel_chapters if audiobook else []
        request = self.context.get("request")
        user = request.user if request else None
        has_locked_chapter = bool(
            audiobook
            and (
                any(not chapter.is_free_preview for chapter in chapters)
                or (audiobook.audio_file and not chapters)
            )
            and not can_access_audiobook(user, audiobook)
        )
        data.update({
            "audiobook_id": audiobook.id if audiobook else None,
            "has_audio": bool(audiobook and (audiobook.audio_file or chapters)),
            "access": audiobook.access if audiobook else None,
            "chapter_count": len(chapters),
            "is_locked": has_locked_chapter,
        })
        return data
    def get_author(self, obj):
        from apps.users.serializers import UserSerializer
        return UserSerializer(obj.author, context=self.context).data
    def _has(self, obj, model):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and model.objects.filter(user=request.user, reel=obj).exists())
    def get_is_liked(self, obj):
        from apps.interactions.models import Like
        return self._has(obj, Like)
    def get_is_saved(self, obj):
        from apps.interactions.models import Save
        return self._has(obj, Save)