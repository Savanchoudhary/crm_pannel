"""
Role-based permission helpers — decorators, mixins, DRF permissions.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import BasePermission

from .models import Role


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------
def role_required(*roles):
    """Decorator that restricts a view to users with specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role in roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped
    return decorator


def admin_required(view_func):
    """Shortcut decorator for admin-only views."""
    return role_required(Role.ADMIN)(view_func)


def calling_required(view_func):
    """Allow calling employees and admins."""
    return role_required(Role.ADMIN, Role.CALLING)(view_func)


def marketing_required(view_func):
    """Allow marketing employees and admins."""
    return role_required(Role.ADMIN, Role.MARKETING)(view_func)


def developer_required(view_func):
    """Allow developers and admins."""
    return role_required(Role.ADMIN, Role.DEVELOPER)(view_func)


# ---------------------------------------------------------------------------
# Class-based view mixins
# ---------------------------------------------------------------------------
class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CallingRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in [Role.ADMIN, Role.CALLING] and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class MarketingRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in [Role.ADMIN, Role.MARKETING] and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DeveloperRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in [Role.ADMIN, Role.DEVELOPER] and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# DRF Permission classes
# ---------------------------------------------------------------------------
class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsCallingUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [Role.ADMIN, Role.CALLING]
        )


class IsMarketingUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [Role.ADMIN, Role.MARKETING]
        )


class IsDeveloperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.role in [Role.ADMIN, Role.DEVELOPER]
        )
