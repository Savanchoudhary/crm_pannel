"""
Signals for accounts app — auto-create EmployeeProfile on User creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, EmployeeProfile


@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    """Automatically create EmployeeProfile when a new User is created."""
    if created and not instance.is_superuser:
        EmployeeProfile.objects.get_or_create(user=instance)
