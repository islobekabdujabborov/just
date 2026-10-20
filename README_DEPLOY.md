# AvoBook — Railway deployment notes

## Required Railway variables

Set these in the Railway service Variables tab:

```text
SECRET_KEY=<long-random-production-secret>
DEBUG=False
ALLOWED_HOSTS=<your-railway-domain>,<your-custom-domain>
CSRF_TRUSTED_ORIGINS=https://<your-railway-domain>,https://<your-custom-domain>
CORS_ALLOWED_ORIGINS=https://<your-custom-domain>
DATABASE_URL=<Railway PostgreSQL connection string>
```

`RAILWAY_PUBLIC_DOMAIN` may also be provided by Railway and is automatically added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` by the Django settings.

## Deployment

Railway builds the React app, copies the production build into the Django image, runs `collectstatic`, runs database migrations at container startup, and starts Gunicorn.

Health check:

```text
/health/
```

API:

```text
/api/
```

Admin:

```text
/admin/
```

## Create the first in-app admin

The AvoBook admin panel uses Django's `is_staff` or `is_superuser` flags. Create the first account from the Railway web service shell (or run the command locally with the Railway service variables available):

```powershell
cd backend
python manage.py createsuperuser
```

With the Railway CLI, run from the repository root:

```powershell
railway run python backend/manage.py createsuperuser
```

To grant panel access to an existing account, use the Railway web service shell or `railway run` with that account's exact username:

```powershell
railway run python backend/manage.py shell -c "from apps.users.models import User; User.objects.filter(username='<username>').update(is_staff=True, is_superuser=True)"
```

Use `is_staff=True` for an admin who may manage Premium, books, and reels. Set `is_superuser=True` only for trusted operators who may also delete user accounts and change staff privileges. The in-app panel is available at `/admin-panel`.

## Media warning

Uploaded images, audio, and video files currently use Django `FileSystemStorage`. Railway's container filesystem is not a durable object-storage solution. For production data that must survive redeploys/restarts, attach a persistent Railway Volume and set `MEDIA_ROOT` to its mount path, or move media to an object-storage provider such as S3-compatible storage.

The application serves `/media/` so uploaded files work in the current container, but persistence depends on the storage configuration.
