from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

def validate_audio(file):
    if file.size > 100 * 1024 * 1024:
        raise ValidationError("Audio files must be 100 MB or smaller.")

class Audiobook(models.Model):
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="audiobooks")
    audio_file = models.FileField(upload_to="audiobooks/", blank=True, validators=[validate_audio, FileExtensionValidator(["mp3", "m4a", "wav", "ogg"])])
    duration = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class Chapter(models.Model):
    audiobook = models.ForeignKey(Audiobook, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200)
    audio_file = models.FileField(upload_to="chapters/", blank=True, validators=[validate_audio, FileExtensionValidator(["mp3", "m4a", "wav", "ogg"])])
    duration = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["audiobook", "order"], name="unique_audiobook_chapter_order")]