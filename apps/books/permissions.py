from django.http import HttpRequest
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.views import APIView


class IsAdminUserOrReadOnly(BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    Read-only access is allowed for everyone.
    """

    def has_permission(self, request: HttpRequest, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)
