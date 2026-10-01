from django.conf import settings
from django.db import models

class ListeningProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listening_progress")
    audiobook = models.ForeignKey("audiobooks.Audiobook", on_delete=models.CASCADE, related_name="progress")
    chapter = models.ForeignKey("audiobooks.Chapter", null=True, blank=True, on_delete=models.SET_NULL)
    position = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "audiobook"], name="unique_user_audiobook_progress")]
        ordering = ["-updated_at"]