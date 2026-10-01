"""
Accounts models — Custom User, Department, EmployeeProfile, ActivityLog.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------
class Role(models.TextChoices):
    ADMIN = 'ADMIN', _('Admin / Boss')
    CALLING = 'CALLING', _('HR Department')
    MARKETING = 'MARKETING', _('Marketing')
    DEVELOPER = 'DEVELOPER', _('Developer')


class EmployeeStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    INACTIVE = 'INACTIVE', _('Inactive')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name

    @property
    def employee_count(self):
        return self.employees.filter(user__is_active=True).count()


# ---------------------------------------------------------------------------
# Custom User Manager
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.ADMIN)
        extra_fields.setdefault('username', email.split('@')[0])
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Custom User
# ---------------------------------------------------------------------------
class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CALLING)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_calling(self):
        return self.role == Role.CALLING

    @property
    def is_marketing(self):
        return self.role == Role.MARKETING

    @property
    def is_developer(self):
        return self.role == Role.DEVELOPER

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        # Generate initials-based fallback
        name = self.get_full_name()
        if name:
            initials = ''.join([p[0].upper() for p in name.split()[:2]])
        else:
            initials = self.email[0].upper()
        return f'/static/img/avatar_default.svg?text={initials}'

    def update_last_seen(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


# ---------------------------------------------------------------------------
# Employee Profile
# ---------------------------------------------------------------------------
class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employees'
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=EmployeeStatus.choices, default=EmployeeStatus.ACTIVE
    )
    # Extra permissions granted by admin
    can_view_calling = models.BooleanField(default=False)
    can_view_marketing = models.BooleanField(default=False)
    can_view_developers = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Employee Profile'
        verbose_name_plural = 'Employee Profiles'
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f'{self.user.full_name} — {self.user.get_role_display()}'

    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Auto-generate employee ID: NC-YYYY-XXXX
            from django.utils import timezone as tz
            year = tz.now().year
            count = EmployeeProfile.objects.filter(
                created_at__year=year
            ).count() + 1
            self.employee_id = f'NC-{year}-{count:04d}'
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------
class ActivityLog(models.Model):
    class ActionType(models.TextChoices):
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        UPLOAD = 'UPLOAD', _('Upload')
        EXPORT = 'EXPORT', _('Export')
        ASSIGN = 'ASSIGN', _('Assign')
        VIEW = 'VIEW', _('View')

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='activity_logs'
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user} — {self.action} — {self.created_at:%Y-%m-%d %H:%M}'
