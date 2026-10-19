# Telegram registration verification

This project supports Telegram-based verification for new AvoBook registrations using `@Abitbook_bot`.

## 1. Create a Telegram bot

The bot already exists. Its username is `Abitbook_bot` (without the `@` prefix). Store the token only in `TELEGRAM_BOT_TOKEN`.

## 2. Configure environment variables

Set these variables on both Railway services and in the local backend environment:

```bash
DATABASE_URL=your-shared-postgresql-connection-string
SECRET_KEY=your-shared-django-secret
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=Abitbook_bot
TELEGRAM_VERIFICATION_CODE_TTL=300
TELEGRAM_VERIFICATION_MAX_ATTEMPTS=5
TELEGRAM_VERIFICATION_RESEND_COOLDOWN=60
TELEGRAM_VERIFICATION_MAX_RESENDS=3
TELEGRAM_VERIFICATION_SESSION_TTL=900
```

The `.env` and `backend/.env` files are ignored by Git. Use placeholders only in `.env.example` files; never put a real token there. The frontend never stores or exposes the token.

## 3. Local development

Apply migrations once, then run the web server and bot in separate terminals from the repository root.

Terminal 1:

```bash
cd backend
python manage.py migrate
python manage.py runserver
```

Terminal 2:

```bash
cd backend
python manage.py run_telegram_bot
```

The bot is a dedicated long-polling process, not a Gunicorn worker or Django startup hook. It cleans up expired verification records on startup and every 10 minutes. Missing `TELEGRAM_BOT_TOKEN` or `TELEGRAM_BOT_USERNAME` causes a clear startup error. Polling retries Telegram network failures with backoff. Keep only one polling instance running: two instances using the same token cause `Conflict: terminated by other getUpdates request`.

## 4. Railway setup

Keep the web service as the only service that runs database migrations. Create a second Railway service named `avobook-bot`:

1. In the Railway project, choose **New** → **GitHub Repo** and select the same repository as the web service.
2. Use the same Dockerfile (`Dockerfile`) and root directory as the web service.
3. In the bot service's **Settings** → **Deploy** → **Start Command**, set exactly:

   ```sh
   cd backend && python manage.py run_telegram_bot
   ```

4. Leave the bot service's **Public Networking** disabled (do not generate a public domain).
5. Leave **Healthcheck Path** empty for the bot service; the bot is a worker and does not serve HTTP.
6. Add the same variables listed above to the bot service as on the web service: `DATABASE_URL`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_VERIFICATION_CODE_TTL`, `TELEGRAM_VERIFICATION_MAX_ATTEMPTS`, `TELEGRAM_VERIFICATION_RESEND_COOLDOWN`, `TELEGRAM_VERIFICATION_MAX_RESENDS`, and `TELEGRAM_VERIFICATION_SESSION_TTL`.
7. Deploy the bot service. Its custom start command replaces the Docker image's web command, so it does not run migrations. Do not run the bot command on the web service or configure more than one bot replica.

The repository's `railway.json` deliberately does not set a healthcheck path because that deployment config applies to each service using it. Keep `/health/` configured in the web service's Railway **Healthcheck Path** setting; leave the bot service's setting empty.

## 5. Database migrations

In local development, run this once before starting services:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

Do not run migrations from `avobook-bot`.

## 6. Full registration flow

1. Open the registration page.
2. Fill in the username, email, and password fields.
3. Click `Telegram orqali tasdiqlash`.
4. The backend creates a secure verification session and returns a Telegram deep link.
5. Open the bot link and press `/start`.
6. The bot validates the payload, links the Telegram account, and sends a fresh 6-digit code.
7. Return to AvoBook, enter the code, and press `Tasdiqlash`.
8. The backend verifies the code, creates the user, and returns JWT tokens.

## 7. Troubleshooting

- If the deep link does not open Telegram, check that `TELEGRAM_BOT_USERNAME` is correct.
- If the bot does not reply, confirm the bot token is valid and the worker is running.
- If verification fails repeatedly, check the `code_expires_at` and `attempts` values in the verification record.
- If the user hits resend too quickly, the cooldown is enforced by backend logic.
- If the bot starts but no code is sent, verify the Telegram account is linked to the correct pending session and the code has not expired.

## 8. Rotating a bot token

1. Create a new bot with BotFather.
2. Set the new `TELEGRAM_BOT_TOKEN` in Railway.
3. Update the worker service environment.
4. Restart the Telegram bot worker.
5. Remove or rotate the old bot token from any previous configuration.

Never log, hardcode, commit, or document the bot token.
