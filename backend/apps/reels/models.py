from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

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

    def save(self, *args, **kwargs):
        file_fields = [field for field in self._meta.concrete_fields if isinstance(field, models.FileField)]
        previous_files = {}
        if self.pk:
            previous_files = Reel.objects.filter(pk=self.pk).values(
                *(field.attname for field in file_fields)
            ).first() or {}
        super().save(*args, **kwargs)
        for field in file_fields:
            previous_name = previous_files.get(field.attname)
            current_file = getattr(self, field.attname)
            current_name = current_file.name if current_file else ""
            if previous_name and previous_name != current_name:
                field.storage.delete(previous_name)



@receiver(post_delete, sender=Reel)
def delete_reel_files(sender, instance, **kwargs):
    for field in instance._meta.concrete_fields:
        if isinstance(field, models.FileField):
            stored_file = getattr(instance, field.attname)
            if stored_file:
                transaction.on_commit(
                    lambda storage=field.storage, name=stored_file.name: storage.delete(name),
                    robust=True,
                )