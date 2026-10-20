from django.conf import settings
from django.db import models


class AdminAuditLog(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_panel_audit_logs",
    )
    admin_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=32)
    target_type = models.CharField(max_length=32)
    target_id = models.PositiveBigIntegerField()
    target_repr = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}: {self.target_type} {self.target_repr}"
