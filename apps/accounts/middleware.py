"""
Middleware for activity tracking and last-seen updates.
"""
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class ActivityLogMiddleware(MiddlewareMixin):
    """Update user last_seen on every authenticated request."""

    UPDATE_INTERVAL_SECONDS = 300  # only update every 5 min to avoid excess DB writes

    # Skip static/media/api calls
    SKIP_PREFIXES = ('/static/', '/media/', '/favicon')

    def process_request(self, request):
        # Skip static files and unauthenticated users
        if any(request.path.startswith(p) for p in self.SKIP_PREFIXES):
            return
        if not hasattr(request, 'user'):
            return
        try:
            if request.user.is_authenticated:
                last_seen = request.user.last_seen
                now = timezone.now()
                if last_seen is None or (now - last_seen).total_seconds() > self.UPDATE_INTERVAL_SECONDS:
                    request.user.update_last_seen()
        except Exception:
            pass  # Never crash the request because of last_seen update
