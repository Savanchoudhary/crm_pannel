"""
Notification views.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from apps.accounts.permissions import admin_required
from apps.accounts.models import User
from .models import Notification, NotificationType


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    # Mark all visible as read
    unread_ids = [n.id for n in page.object_list if not n.is_read]
    if unread_ids:
        Notification.objects.filter(id__in=unread_ids).update(
            is_read=True, read_at=timezone.now()
        )

    return render(request, 'notifications/list.html', {
        'notifications': page,
    })


@login_required
@require_POST
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.read_at = timezone.now()
    notif.save()
    return JsonResponse({'status': 'read'})


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())
    return JsonResponse({'status': 'all_read'})


@admin_required
def send_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        target_role = request.POST.get('target_role', '')

        if not title or not message:
            return JsonResponse({'error': 'Title and message required.'}, status=400)

        recipients = User.objects.filter(is_active=True)
        if target_role:
            recipients = recipients.filter(role=target_role)

        notifications = [
            Notification(
                recipient=user,
                title=title,
                message=message,
                notification_type=NotificationType.ANNOUNCEMENT,
            )
            for user in recipients
        ]
        Notification.objects.bulk_create(notifications)
        return JsonResponse({'status': 'sent', 'count': len(notifications)})

    return render(request, 'notifications/announcement.html')
