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

## Media warning

Uploaded images, audio, and video files currently use Django `FileSystemStorage`. Railway's container filesystem is not a durable object-storage solution. For production data that must survive redeploys/restarts, attach a persistent Railway Volume and set `MEDIA_ROOT` to its mount path, or move media to an object-storage provider such as S3-compatible storage.

The application serves `/media/` so uploaded files work in the current container, but persistence depends on the storage configuration.
