from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

def validate_video(file):
    if file.size > 100 * 1024 * 1024:
        raise ValidationError("Video files must be 100 MB or smaller.")

class Reel(models.Model):
    video = models.FileField(upload_to="reels/", blank=True, validators=[validate_video, FileExtensionValidator(["mp4", "mov", "webm"])])
    book = models.ForeignKey("books.Book", on_delete=models.SET_NULL, null=True, blank=True, related_name="reels")
    caption = models.CharField(max_length=500, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reels")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ["-created_at"]