from django.conf import settings
from django.db import models

class Notification(models.Model):
    TYPES = [(value, value.replace("_", " ").title()) for value in ["like", "comment", "follow", "save", "new_audiobook", "new_chapter"]]
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_notifications")
    type = models.CharField(max_length=24, choices=TYPES)
    text = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ["-created_at"]