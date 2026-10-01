from rest_framework.permissions import SAFE_METHODS, BasePermission

class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or getattr(obj, "owner_id", None) == request.user.id or getattr(obj, "author_id", None) == request.user.id or getattr(obj, "created_by_id", None) == request.user.id