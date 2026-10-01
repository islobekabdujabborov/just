from django.conf import settings
from django.db import models

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    reel = models.ForeignKey("reels.Reel", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField(max_length=2000)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ["created_at"]

class CommentLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "comment"], name="unique_comment_like")]