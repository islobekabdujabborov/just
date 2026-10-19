from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from apps.telegram_bot.handlers import cancel_command, help_command, start_command


class Command(BaseCommand):
    help = "Run the AvoBook Telegram verification bot."

    def handle(self, *args, **options):
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
        bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
        if not bot_token:
            raise CommandError("TELEGRAM_BOT_TOKEN environment variable is required.")
        if not bot_username:
            raise CommandError("TELEGRAM_BOT_USERNAME environment variable is required.")

        app = ApplicationBuilder().token(bot_token).build()
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("cancel", cancel_command))

        self.stdout.write(self.style.SUCCESS(f"Starting Telegram bot for @{bot_username}..."))
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
