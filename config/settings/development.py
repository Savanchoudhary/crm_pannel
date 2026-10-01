"""
Development settings for Novem Controls CRM.
"""
from .base import *

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Debug toolbar (optional, install django-debug-toolbar if needed)
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Simpler static files in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Disable password validation in dev for convenience
AUTH_PASSWORD_VALIDATORS = []

# More verbose logging in development
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

# ── DATABASE OVERRIDE ──────────────────────────────────────────────────────
# Use SQLite for local development (no PostgreSQL required).
# Switch to PostgreSQL in production by removing/commenting these lines.
import os
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
