"""
Inject unread notification count into all templates.
"""


def notifications_processor(request):
    if not hasattr(request, 'user'):
        return {'unread_notification_count': 0, 'recent_notifications': []}

    if request.user.is_authenticated:
        try:
            from .models import Notification
            unread_count = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()
            recent_notifications = Notification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:5]
            return {
                'unread_notification_count': unread_count,
                'recent_notifications': recent_notifications,
            }
        except Exception:
            pass
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }
