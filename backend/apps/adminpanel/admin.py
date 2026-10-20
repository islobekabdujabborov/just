from django.contrib import admin

from .models import AdminAuditLog


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "admin_username", "action", "target_type", "target_id", "target_repr")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("admin_username", "target_repr", "target_id")
    readonly_fields = (
        "admin",
        "admin_username",
        "action",
        "target_type",
        "target_id",
        "target_repr",
        "details",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
