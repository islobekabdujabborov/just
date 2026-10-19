from django.contrib import admin
from .models import Audiobook, Bookmark, Chapter

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ["title", "audio_file", "duration", "order", "is_free_preview"]
@admin.register(Audiobook)
class AudiobookAdmin(admin.ModelAdmin):
    list_display = ["book", "access", "duration", "created_by", "created_at"]
    search_fields = ["book__title", "book__author__name"]
    list_filter = ["access", "created_at"]
    ordering = ["-created_at"]
    inlines = [ChapterInline]
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "audiobook", "order", "duration", "is_free_preview"]
    search_fields = ["title", "audiobook__book__title"]
    list_filter = ["audiobook"]
    ordering = ["audiobook", "order"]
@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ["user", "audiobook", "chapter", "position", "created_at"]
    search_fields = ["user__username", "audiobook__book__title", "note"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]