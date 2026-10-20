from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.users.models import Subscription, User
from .models import AdminAuditLog


class AdminPanelUserSerializer(serializers.ModelSerializer):
    is_premium = serializers.BooleanField(read_only=True)
    premium_expires_at = serializers.DateTimeField(read_only=True, allow_null=True)
    books_count = serializers.IntegerField(read_only=True)
    reels_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_premium",
            "premium_expires_at",
            "date_joined",
            "books_count",
            "reels_count",
            "is_staff",
            "is_active",
        ]


class PremiumGrantSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["monthly", "yearly", "custom"])
    days = serializers.IntegerField(required=False, min_value=1, max_value=3650)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["plan"] == Subscription.PLAN_CUSTOM and "days" not in attrs:
            raise serializers.ValidationError({"days": "Maxsus tarif uchun kunlar sonini kiriting."})
        if attrs["plan"] != Subscription.PLAN_CUSTOM and "days" in attrs:
            raise serializers.ValidationError({"days": "Kunlar soni faqat maxsus tarif uchun beriladi."})
        return attrs


class AdminPanelUserUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Kamida bitta maydonni yuboring.")
        request = self.context["request"]
        if "is_staff" in attrs and not request.user.is_superuser:
            raise PermissionDenied("Staff holatini faqat superuser o'zgartira oladi.")
        return attrs


class AdminAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminAuditLog
        fields = [
            "id",
            "admin_username",
            "action",
            "target_type",
            "target_id",
            "target_repr",
            "details",
            "created_at",
        ]


def active_subscription_queryset():
    return Subscription.objects.filter(
        status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_CANCELED],
        expires_at__gt=timezone.now(),
    )
