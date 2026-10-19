import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from apps.telegram_bot.handlers import cancel_command, help_command, start_command
from apps.users.services import cleanup_expired_verifications

logger = logging.getLogger(__name__)
CLEANUP_INTERVAL_SECONDS = 10 * 60


class _TokenRedactionFilter(logging.Filter):
    def __init__(self, token):
        super().__init__()
        self.token = token

    def filter(self, record):
        if not self.token:
            return True
        record.msg = record.getMessage().replace(self.token, "[REDACTED]")
        record.args = ()
        if record.exc_info:
            formatted_exception = logging.Formatter().formatException(record.exc_info)
            record.exc_text = formatted_exception.replace(self.token, "[REDACTED]")
        return True


def _install_token_redaction_filter(token):
    token_filter = _TokenRedactionFilter(token)
    for logger_name, candidate in logging.Logger.manager.loggerDict.items():
        if isinstance(candidate, logging.Logger) and logger_name.startswith(("telegram", "httpx")):
            candidate.addFilter(token_filter)
            for handler in candidate.handlers:
                handler.addFilter(token_filter)
    for handler in logging.getLogger().handlers:
        handler.addFilter(token_filter)
    if logging.lastResort is not None:
        logging.lastResort.addFilter(token_filter)


async def _periodic_verification_cleanup(application):
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            await sync_to_async(cleanup_expired_verifications, thread_sensitive=True)()
        except Exception as exc:
            logger.error("Expired verification cleanup failed (%s).", type(exc).__name__)


async def _start_verification_cleanup(application):
    application.bot_data["verification_cleanup_task"] = asyncio.create_task(
        _periodic_verification_cleanup(application)
    )


async def _stop_verification_cleanup(application):
    task = application.bot_data.pop("verification_cleanup_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def _handle_update_error(update, context):
    error = context.error
    logger.error("Telegram update failed (%s).", type(error).__name__)


class Command(BaseCommand):
    help = "Run the AvoBook Telegram verification bot."

    def handle(self, *args, **options):
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)

        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
        if not bot_token:
            raise CommandError("TELEGRAM_BOT_TOKEN environment variable is required.")
        if not bot_username:
            raise CommandError("TELEGRAM_BOT_USERNAME environment variable is required.")

        _install_token_redaction_filter(bot_token)

        try:
            cleanup_expired_verifications()
        except Exception as exc:
            raise CommandError(
                f"Could not clean up expired Telegram verifications ({type(exc).__name__})."
            ) from exc

        app = (
            ApplicationBuilder()
            .token(bot_token)
            .post_init(_start_verification_cleanup)
            .post_shutdown(_stop_verification_cleanup)
            .build()
        )
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        app.add_error_handler(_handle_update_error)

        self.stdout.write(self.style.SUCCESS(f"Starting Telegram bot for @{bot_username}..."))
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            bootstrap_retries=-1,
        )
