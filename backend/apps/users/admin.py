from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Follow, Subscription, User

@admin.register(User)
class AvoUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("AvoBook profile", {"fields": ("avatar", "bio", "location")}),)
    list_display = ["username", "email", "is_staff", "followers_count", "date_joined"]
    search_fields = ["username", "email"]
    ordering = ["-date_joined"]

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "followed", "created_at"]
    search_fields = ["follower__username", "followed__username"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "started_at", "expires_at", "provider"]
    list_filter = ["plan", "status", "provider"]
    search_fields = ["user__username", "user__email", "provider_ref"]
    ordering = ["-started_at"]