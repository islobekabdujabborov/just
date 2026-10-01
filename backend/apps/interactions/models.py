from django.conf import settings
from django.db import models

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reel = models.ForeignKey("reels.Reel", on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "reel"], condition=models.Q(reel__isnull=False), name="unique_reel_like"),
            models.UniqueConstraint(fields=["user", "book"], condition=models.Q(book__isnull=False), name="unique_book_like"),
        ]

class Save(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reel = models.ForeignKey("reels.Reel", on_delete=models.CASCADE, null=True, blank=True, related_name="saves")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, null=True, blank=True, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "reel"], condition=models.Q(reel__isnull=False), name="unique_reel_save"),
            models.UniqueConstraint(fields=["user", "book"], condition=models.Q(book__isnull=False), name="unique_book_save"),
        ]