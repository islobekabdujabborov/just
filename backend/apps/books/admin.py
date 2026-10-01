from django.contrib import admin
from .models import Author, Book, Genre

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "genre", "language", "rating", "created_at"]
    list_filter = ["genre", "language", "created_at"]
    search_fields = ["title", "author__name", "description"]
    ordering = ["-created_at"]
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]
    ordering = ["name"]
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    ordering = ["name"]