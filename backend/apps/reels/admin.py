from django.contrib import admin
from .models import Reel

@admin.register(Reel)
class ReelAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "book", "caption", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["author__username", "book__title", "caption"]
    ordering = ["-created_at"]