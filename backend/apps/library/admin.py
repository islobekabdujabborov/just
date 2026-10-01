from django.contrib import admin
from .models import ListeningProgress

@admin.register(ListeningProgress)
class ListeningProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "audiobook", "chapter", "position", "percentage", "updated_at"]
    list_filter = ["updated_at"]
    search_fields = ["user__username", "audiobook__book__title"]
    ordering = ["-updated_at"]