# Novem Controls CRM

Novem Controls CRM is a Django-based business management platform for employees, leads, calling workflows, marketing operations, attendance tracking, locations, notifications, and reporting.

## Requirements

- Python 3.11+
- PostgreSQL for production deployment
- SQLite for local development by default
- A virtual environment is recommended for local setup

## Local Setup

From PowerShell:

```powershell
cd "C:\path\to\novem_crm"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

If PowerShell blocks script activation, run the project using the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## Initial Admin

Create the first administrator account:

```powershell
python manage.py createsuperuser
```

The CRM setup command can create initial sample data and CRM defaults:

```powershell
python manage.py setup_crm
```

Do not run sample-data commands in production unless you explicitly want demo records.

## Environment Variables

Copy `.env.example` to `.env` and customize it for your environment. Development uses SQLite by default, but production should use a managed PostgreSQL instance.

Important values include:

- `SECRET_KEY`: unique long secret key for production
- `DEBUG`: set to `False` in production
- `ALLOWED_HOSTS`: comma-separated hostnames, for example `localhost,127.0.0.1,.vercel.app`
- `DATABASE_URL`: PostgreSQL connection string for production deployments
- `CSRF_TRUSTED_ORIGINS`: comma-separated HTTPS origins, for example `https://your-domain.com`
- `COMPANY_NAME`: company name displayed across the app
- `TIMEZONE`: application timezone, such as `Asia/Kolkata`

Never commit `.env`, database passwords, or production secrets.

Example local configuration:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:password@localhost:5432/novem_crm
CSRF_TRUSTED_ORIGINS=http://localhost:8000
COMPANY_NAME=Novem Controls
TIMEZONE=Asia/Kolkata
```

## Useful Commands

```powershell
python manage.py check
python manage.py check --deploy
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py test
```

## Production Deployment

This project is configured for production with secure defaults in `config/settings/production.py`.

Key production settings include:

- `DEBUG = False`
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`
- database configuration from `DATABASE_URL` when available

### Render deployment

The repository includes [`render.yaml`](render.yaml) for a Render Blueprint. It defines a Python web service and a managed PostgreSQL database.

1. Push the project to a GitHub repository.
2. In Render, choose **New > Blueprint**.
3. Connect the repository and select the project.
4. Render installs dependencies, collects static files, runs migrations, and starts Gunicorn.
5. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the final public hostname if the service is renamed.
6. Create an admin account after the first deploy:

```bash
python manage.py createsuperuser
```

The production entry point is `config.wsgi:application`.

### Vercel / hosted frontend deployment

The production settings also support hostnames ending in `.vercel.app`. If you deploy to Vercel or another managed host, make sure the environment variables match the live domain:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=.vercel.app,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://your-app-name.vercel.app
DATABASE_URL=postgres://user:password@host:5432/dbname
```

Uploaded media files should be stored in persistent storage or a dedicated object store, because local filesystem storage is not durable in cloud deployments.

## Project Structure

- `apps/`: Django applications
- `config/`: Django settings and deployment configuration
- `templates/`: HTML templates
- `static/`: source static assets
- `media/`: uploaded local files
- `manage.py`: Django management CLI
- `render.yaml`: Render deployment blueprint
