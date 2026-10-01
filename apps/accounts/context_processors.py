"""
Context processors for accounts app.
"""
from django.conf import settings


def company_context(request):
    """Inject company name and user role into every template."""
    context = {
        'COMPANY_NAME': getattr(settings, 'COMPANY_NAME', 'Novem Controls'),
    }
    if not hasattr(request, 'user'):
        return context
    if request.user.is_authenticated:
        context['current_user_role'] = request.user.role
        context['is_admin'] = request.user.is_admin
        try:
            context['employee_profile'] = request.user.profile
        except Exception:
            context['employee_profile'] = None
        # Overdue follow-up count for sidebar badge
        try:
            from apps.calling.models import FollowUp
            from django.utils import timezone
            context['overdue_count'] = FollowUp.objects.filter(
                assigned_to=request.user,
                follow_up_date__lt=timezone.now().date(),
                is_completed=False,
            ).count()
        except Exception:
            context['overdue_count'] = 0
    return context
