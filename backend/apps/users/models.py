from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    bio = models.CharField(max_length=500, blank=True)
    location = models.CharField(max_length=120, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    REQUIRED_FIELDS = ["email"]

    @property
    def private_account(self):
        preferences = self.notification_preferences or {}
        if not isinstance(preferences, dict):
            return False
        return bool(preferences.get("privateAccount", False))

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    def notification_enabled(self, key, default=True):
        preferences = self.notification_preferences or {}
        if not isinstance(preferences, dict):
            return default
        return preferences.get(key, default)

    def can_view_profile(self, viewer):
        if viewer is None or not viewer.is_authenticated:
            return not self.private_account
        if viewer.pk == self.pk:
            return True
        if not self.private_account:
            return True
        return Follow.objects.filter(follower=viewer, followed=self).exists()

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["follower", "followed"], name="unique_user_follow")]
        indexes = [models.Index(fields=["followed", "-created_at"])]