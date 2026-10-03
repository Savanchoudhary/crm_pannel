"""
Production settings for Novem Controls CRM.
"""
from .base import *
import dj_database_url

DEBUG = False

# Security settings
# Security settings
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='.vercel.app,localhost,127.0.0.1',
    cast=Csv()
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://crm-pannel-7i5v.vercel.app',
    cast=Csv()
)

# Render and other managed hosts provide the connection string directly.
if config('DATABASE_URL', default=''):
	DATABASES['default'] = dj_database_url.parse(
		config('DATABASE_URL'), conn_max_age=600, ssl_require=True
	)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Use database-backed sessions in production
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
