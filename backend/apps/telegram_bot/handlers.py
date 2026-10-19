import logging

from telegram import Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import ContextTypes

from apps.users.services import link_telegram_account

logger = logging.getLogger(__name__)


async def _reply_error(update: Update, text: str):
    if update.message is None:
        return
    try:
        await update.message.reply_text(text)
    except (Forbidden, TelegramError):
        logger.warning("Telegram reply blocked or failed: %s", text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    payload = (context.args[0] if context.args else "").strip()
    if not payload:
        await _reply_error(update, "AvoBook ro'yxatdan o'tish havolasi noto'g'ri. Iltimos, sayt orqali yangi havola oling.")
        return
    try:
        linked = link_telegram_account(payload, update.effective_user.id if update.effective_user else 0, update.effective_user.username if update.effective_user else "")
    except Exception:
        await _reply_error(update, "Havola yaroqsiz yoki muddati tugagan. AvoBook saytiga qaytib yangi tasdiqlashni boshlang.")
        return

    code = linked.get("code")
    if code:
        text = (
            f"Assalomu alaykum! AvoBook ro‘yxatdan o‘tishni tasdiqlash kodi: {code}.\n\n"
            "Kod 5 daqiqa davomida amal qiladi. Uni AvoBook saytiga kiriting. "
            "Ushbu kodni boshqa odamlarga bermang."
        )
        try:
            await update.message.reply_text(text)
        except (Forbidden, TelegramError):
            logger.warning("Telegram send_message failed for code delivery.")
    else:
        await _reply_error(update, "Bu havola allaqachon ishlatilgan yoki tasdiqlangan. AvoBook saytiga qaytib, yangi tasdiqlashni boshlang.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    text = (
        "AvoBook ro'yxatdan o'tish uchun sayt orqali yaratilgan havoladan foydalaning.\n\n"
        "/start - tasdiqlashni boshlash\n"
        "/help - yordam\n"
        "/cancel - tasdiqlashni bekor qilish"
    )
    try:
        await update.message.reply_text(text)
    except (Forbidden, TelegramError):
        logger.warning("Help reply failed.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    try:
        await update.message.reply_text("Tasdiqlash bekor qilindi. AvoBook saytiga qaytib, qayta boshlashingiz mumkin.")
    except (Forbidden, TelegramError):
        logger.warning("Cancel reply failed.")
