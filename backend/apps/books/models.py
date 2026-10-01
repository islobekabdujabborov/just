from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

def validate_cover(file):
    if file.size > 8 * 1024 * 1024:
        from django.core.exceptions import ValidationError
        raise ValidationError("Cover image must be 8 MB or smaller.")

class Author(models.Model):
    name = models.CharField(max_length=180, unique=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    def __str__(self): return self.name

class Book(models.Model):
    title = models.CharField(max_length=240, db_index=True)
    author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="books")
    cover = models.ImageField(upload_to="books/", blank=True, validators=[validate_cover, FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    description = models.TextField(blank=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="books")
    language = models.CharField(max_length=12, default="uz")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_books")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["genre", "-created_at"]), models.Index(fields=["-rating"])]
    def __str__(self): return self.title