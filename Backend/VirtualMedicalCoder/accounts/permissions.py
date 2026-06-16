from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access only to authenticated admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )