from rest_framework.permissions import BasePermission


class IsCitizen(BasePermission):
    """Allows access only to users with role='citizen'."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "citizen"
        )


class IsOfficer(BasePermission):
    """Allows access only to field officers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("officer", "admin")
        )


class IsAdmin(BasePermission):
    """Allows access only to admin users."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level: owner of the object or an admin can access."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        return getattr(obj, "user", None) == request.user
