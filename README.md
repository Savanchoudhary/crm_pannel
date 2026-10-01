# Novem Controls CRM

Django-based CRM for managing employees, leads, calling, marketing, developers, attendance, locations, notifications, and reports.

## Requirements

- Python 3.11+
- PostgreSQL for production
- SQLite is used automatically in development

## Local Setup

From PowerShell:

```powershell
cd "C:\Users\pc\Desktop\CRM K\novem_crm"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

If PowerShell blocks script activation, run the server with the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## Initial Admin

Create an administrator interactively:

```powershell
python manage.py createsuperuser
```

The optional CRM setup command can create the initial CRM data and sample accounts:

```powershell
python manage.py setup_crm
```

Do not run sample-data commands in production unless you explicitly want sample records.

## Environment Variables

Copy `.env.example` to `.env` for local configuration. Development uses SQLite by default. Important values include:

- `SECRET_KEY`: long random secret in production
- `DEBUG`: `False` in production
- `ALLOWED_HOSTS`: comma-separated hostnames
- `DATABASE_URL`: PostgreSQL connection URL for production
- `CSRF_TRUSTED_ORIGINS`: comma-separated HTTPS origins
- `COMPANY_NAME`: displayed company name
- `TIMEZONE`: application timezone

Never commit `.env`, passwords, or production secrets.

## Useful Commands

```powershell
python manage.py check
python manage.py check --deploy
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py test
```

## Render Deployment

The repository includes [`render.yaml`](render.yaml) for a Render Blueprint. It defines a Python web service and a managed PostgreSQL database.

1. Push the `novem_crm` folder to a GitHub repository.
2. In Render, choose **New > Blueprint**.
3. Connect the GitHub repository and select it.
4. Render reads `render.yaml`, installs dependencies, collects static files, runs migrations, and starts Gunicorn.
5. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the final Render hostname if you rename the service.
6. Create an admin after the first deploy using the Render Shell:

```bash
python manage.py createsuperuser
```

The production entry point is `config.wsgi:application`. Uploaded media files require persistent storage or external object storage because local deployment disk is not durable.

## Project Structure

- `apps/`: Django applications
- `config/`: Django settings and URL/WSGI configuration
- `templates/`: HTML templates
- `static/`: source static assets
- `media/`: local uploaded files
- `manage.py`: Django management CLI
