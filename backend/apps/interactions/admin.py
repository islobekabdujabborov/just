from django.contrib import admin
from .models import Like, Save

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "reel", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "book__title", "reel__caption"]
    ordering = ["-created_at"]
@admin.register(Save)
class SaveAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "reel", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "book__title", "reel__caption"]
    ordering = ["-created_at"]