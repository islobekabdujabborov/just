from django.contrib import admin
from .models import Audiobook, Chapter

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
@admin.register(Audiobook)
class AudiobookAdmin(admin.ModelAdmin):
    list_display = ["book", "duration", "created_by", "created_at"]
    search_fields = ["book__title", "book__author__name"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]
    inlines = [ChapterInline]
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "audiobook", "order", "duration"]
    search_fields = ["title", "audiobook__book__title"]
    list_filter = ["audiobook"]
    ordering = ["audiobook", "order"]