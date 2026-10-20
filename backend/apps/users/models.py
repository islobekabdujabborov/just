import hashlib

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class SubscriptionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=["active", "canceled"], expires_at__gt=timezone.now())


class SubscriptionManager(models.Manager.from_queryset(SubscriptionQuerySet)):
    def active_for(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.get_queryset().active().filter(user=user)


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


class Subscription(models.Model):
    PLAN_MONTHLY = "monthly"
    PLAN_YEARLY = "yearly"
    PLAN_CUSTOM = "custom"
    PLAN_CHOICES = [
        (PLAN_MONTHLY, "Monthly"),
        (PLAN_YEARLY, "Yearly"),
        (PLAN_CUSTOM, "Custom"),
    ]
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.CharField(max_length=16, choices=PLAN_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=32, blank=True, default="")
    provider_ref = models.CharField(max_length=255, blank=True, default="")
    admin_note = models.CharField(max_length=500, blank=True, default="")

    objects = SubscriptionManager()

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_user",
            ),
        ]

    @property
    def grants_access(self):
        return self.status in {self.STATUS_ACTIVE, self.STATUS_CANCELED} and self.expires_at > timezone.now()


class TelegramVerification(models.Model):
    STATUS_PENDING = "pending"
    STATUS_LINKED = "linked"
    STATUS_VERIFIED = "verified"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_LINKED, "Linked"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    session_token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    start_payload_hash = models.CharField(max_length=128, unique=True, db_index=True)
    username = models.CharField(max_length=150)
    email = models.EmailField()
    password_hash = models.CharField(max_length=255, blank=True, default="")
    telegram_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    code_hash = models.CharField(max_length=128, blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)
    resend_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    code_expires_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    code_used_at = models.DateTimeField(null=True, blank=True)
    last_resend_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["telegram_user_id", "status"]),
            models.Index(fields=["email", "status"]),
        ]

    def is_active(self):
        return self.status in {self.STATUS_PENDING, self.STATUS_LINKED} and self.expires_at > timezone.now() and not self.code_used_at

    @staticmethod
    def hash_value(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def matches_token(self, token):
        return self.session_token_hash == self.hash_value(token)

    def matches_payload(self, payload):
        return self.start_payload_hash == self.hash_value(payload)

    def code_matches(self, code):
        if not self.code_hash or not code:
            return False
        return self.code_hash == self.hash_value(str(code).strip())


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["follower", "followed"], name="unique_user_follow")]
        indexes = [models.Index(fields=["followed", "-created_at"])]