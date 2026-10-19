# Telegram registration verification

This project supports a real Telegram-based verification flow for new AvoBook registrations.

## 1. Create a Telegram bot

1. Open Telegram and search for `@BotFather`.
2. Run `/newbot`.
3. Choose a friendly bot name and username.
4. Copy the bot token that BotFather returns.
5. Save the username as `your_bot_username` without the `@` prefix.

## 2. Configure environment variables

Set these values in the backend environment used by the Django app (including Railway):

```bash
TELEGRAM_BOT_TOKEN=replace-with-your-bot-token
TELEGRAM_BOT_USERNAME=your_bot_username_without_at
TELEGRAM_VERIFICATION_CODE_TTL=300
TELEGRAM_VERIFICATION_MAX_ATTEMPTS=5
TELEGRAM_VERIFICATION_RESEND_COOLDOWN=60
TELEGRAM_VERIFICATION_MAX_RESENDS=3
TELEGRAM_VERIFICATION_SESSION_TTL=900
```

The frontend never stores or exposes the token.

## 3. Local development

From the project root:

```bash
cd backend
python manage.py migrate
python manage.py run_telegram_bot
```

The bot runs as a dedicated polling worker and is not started from Gunicorn or Django app startup hooks.

## 4. Railway setup

Create a separate Railway service, using the same repository, and set the same environment variables there.

Recommended architecture:

- Web service: Django app with Gunicorn
- Worker service: same repo, command `cd backend && python manage.py run_telegram_bot`
- Shared database: use the same `DATABASE_URL`
- Shared secret values: `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, etc.

Do not start polling from the web service process.

## 5. Database migrations

Run:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

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

## 8. Rotating a leaked bot token

1. Create a new bot with BotFather.
2. Set the new `TELEGRAM_BOT_TOKEN` in Railway.
3. Update the worker service environment.
4. Restart the Telegram bot worker.
5. Remove or rotate the old bot token from any previous configuration.

Do not hardcode bot secrets in the frontend or repository.
