# Build the React frontend separately so node_modules never enters the runtime image.
FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src ./src
RUN npm run build

# Django runtime
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY --from=frontend /app/dist ./dist

# Static assets are collected at image build time; no database is required for this step.
RUN SECRET_KEY=build-only-placeholder DEBUG=False python backend/manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "cd backend && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 120 --forwarded-allow-ips='*'"]
