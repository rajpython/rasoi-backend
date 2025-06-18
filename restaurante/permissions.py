# from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsManager(BasePermission):
    def has_permission(self, request, view):
       if request.user.groups.filter(name='Managers').exists():
            return True

class IsDeliveryCrew(BasePermission):
    def has_permission(self, request, view):
       if request.user.groups.filter(name='Delivery crew').exists():
            return True

class IsManagerOrAdminForSafe(BasePermission):
    """
    Allow unrestricted access for safe methods (GET, HEAD, OPTIONS).
    Allow POST, PUT, PATCH, DELETE only for admin or manager users.
    """
    def has_permission(self, request, view):
        # Safe methods require no auth
        if request.method in SAFE_METHODS:
            return True

        # Unsafe methods require authentication and proper group/staff
        user = request.user
        return (
            user and user.is_authenticated and (
                user.is_staff or
                user.groups.filter(name='Managers').exists()
            )
        )
