from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from .models import Author, Book, Genre, validate_cover

class AuthorSerializer(serializers.ModelSerializer):
    class Meta: model = Author; fields = ["id", "name", "bio"]

class GenreSerializer(serializers.ModelSerializer):
    class Meta: model = Genre; fields = ["id", "name", "slug"]

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_name = serializers.CharField(write_only=True, required=False)
    genre = serializers.SlugRelatedField(slug_field="name", queryset=Genre.objects.all())
    cover = serializers.ImageField(required=False, validators=[validate_cover, FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    t = serializers.CharField(source="title", read_only=True)
    a = serializers.CharField(source="author.name", read_only=True)
    g = serializers.CharField(source="genre.name", read_only=True)
    r = serializers.DecimalField(source="rating", max_digits=3, decimal_places=1, read_only=True)
    d = serializers.SerializerMethodField()
    dsc = serializers.CharField(source="description", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    class Meta:
        model = Book
        fields = ["id", "title", "author", "author_name", "cover", "description", "genre", "language", "rating", "duration", "created_at", "updated_at", "t", "a", "g", "r", "d", "dsc", "likes_count", "is_liked", "is_saved"]
        read_only_fields = ["id", "created_at", "updated_at", "likes_count", "is_liked", "is_saved"]
    def get_d(self, obj):
        return f"{obj.duration // 3600}s {obj.duration % 3600 // 60:02d}d" if obj.duration else ""
    def _has(self, obj, model):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and model.objects.filter(user=request.user, book=obj).exists())
    def get_is_liked(self, obj):
        from apps.interactions.models import Like
        return self._has(obj, Like)
    def get_is_saved(self, obj):
        from apps.interactions.models import Save
        return self._has(obj, Save)
    def create(self, validated_data):
        author_name = validated_data.pop("author_name", "Unknown author")
        author, _ = Author.objects.get_or_create(name=author_name)
        request = self.context.get("request")
        owner = validated_data.pop("owner", request.user if request and request.user.is_authenticated else None)
        return Book.objects.create(author=author, owner=owner, **validated_data)
    def update(self, instance, validated_data):
        author_name = validated_data.pop("author_name", None)
        if author_name:
            instance.author, _ = Author.objects.get_or_create(name=author_name)
        return super().update(instance, validated_data)