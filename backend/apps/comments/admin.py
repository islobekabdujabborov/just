from django.contrib import admin
from .models import Comment, CommentLike

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["user", "reel", "text", "parent", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "text", "reel__caption"]
    ordering = ["-created_at"]
@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ["user", "comment"]
    search_fields = ["user__username", "comment__text"]