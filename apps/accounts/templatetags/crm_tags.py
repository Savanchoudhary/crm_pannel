"""
Custom template tags and filters for the CRM.
"""
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.filter
def role_badge(role):
    """Return Bootstrap badge HTML for a role."""
    colors = {
        'ADMIN': 'danger',
        'CALLING': 'primary',
        'MARKETING': 'success',
        'DEVELOPER': 'warning',
    }
    labels = {
        'ADMIN': 'Admin',
        'CALLING': 'HR Department',
        'MARKETING': 'Marketing',
        'DEVELOPER': 'Developer',
    }
    color = colors.get(role, 'secondary')
    label = labels.get(role, role)
    return f'<span class="badge bg-{color}">{label}</span>'


@register.filter
def status_badge(status):
    """Return Bootstrap badge HTML for lead/call status."""
    colors = {
        'PENDING': 'secondary',
        'CALLING': 'primary',
        'COMPLETED': 'success',
        'NO_ANSWER': 'warning',
        'BUSY': 'warning',
        'INTERESTED': 'success',
        'NOT_INTERESTED': 'danger',
        'FOLLOW_UP': 'info',
        'IN_PROGRESS': 'primary',
        'ON_HOLD': 'warning',
        'CANCELLED': 'danger',
        'ACTIVE': 'success',
        'INACTIVE': 'danger',
        'ON_LEAVE': 'warning',
    }
    color = colors.get(status, 'secondary')
    label = status.replace('_', ' ').title()
    return f'<span class="badge bg-{color}">{label}</span>'


@register.filter
def duration_display(seconds):
    """Format seconds as 'Xh Ym Zs' or 'Ym Zs'."""
    if not seconds:
        return '—'
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}h {m}m {s}s'
    elif m:
        return f'{m}m {s}s'
    return f'{s}s'


@register.filter
def time_ago(dt):
    """Return 'X minutes ago' style string."""
    if not dt:
        return '—'
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        m = seconds // 60
        return f'{m} minute{"s" if m != 1 else ""} ago'
    elif seconds < 86400:
        h = seconds // 3600
        return f'{h} hour{"s" if h != 1 else ""} ago'
    else:
        d = seconds // 86400
        return f'{d} day{"s" if d != 1 else ""} ago'


@register.simple_tag
def active_nav(request, url_name):
    """Return 'active' if the current URL matches the given name."""
    from django.urls import resolve, Resolver404
    try:
        current = resolve(request.path_info)
        if current.url_name == url_name or current.view_name == url_name:
            return 'active'
    except Resolver404:
        pass
    return ''


@register.simple_tag
def active_nav_prefix(request, prefix):
    """Return 'active' if request path starts with given prefix."""
    if request.path.startswith(prefix):
        return 'active'
    return ''


@register.filter
def percentage(value, total):
    """Calculate percentage safely."""
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ZeroDivisionError, TypeError, ValueError):
        return 0


@register.inclusion_tag('partials/avatar.html')
def user_avatar(user, size='sm'):
    return {'user': user, 'size': size}


@register.filter
def dict_key(d, key):
    """Access dictionary by key in templates."""
    try:
        return d.get(key, '')
    except AttributeError:
        return ''


@register.filter
def split(value, sep):
    """Split a string by separator."""
    return value.split(sep)
