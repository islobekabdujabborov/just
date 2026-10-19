import asyncio
import logging

from telegram import Update
from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError
from telegram.ext import ContextTypes

from apps.users.services import link_telegram_account

logger = logging.getLogger(__name__)
MAX_REPLY_ATTEMPTS = 4


async def _reply_error(update: Update, text: str):
    if update.message is None:
        return
    for attempt in range(MAX_REPLY_ATTEMPTS):
        try:
            await update.message.reply_text(text)
            return
        except Forbidden:
            logger.warning("Telegram reply was blocked.")
            return
        except RetryAfter as exc:
            if attempt + 1 == MAX_REPLY_ATTEMPTS:
                logger.warning("Telegram reply remained rate limited.")
                return
            retry_after = exc.retry_after.total_seconds() if hasattr(exc.retry_after, "total_seconds") else exc.retry_after
            await asyncio.sleep(min(float(retry_after), 30))
        except NetworkError:
            if attempt + 1 == MAX_REPLY_ATTEMPTS:
                logger.warning("Telegram reply failed after network retries.")
                return
            await asyncio.sleep(2**attempt)
        except TelegramError as exc:
            logger.warning("Telegram reply failed (%s).", type(exc).__name__)
            return


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    payload = (context.args[0] if context.args else "").strip()
    if not payload:
        await _reply_error(update, "AvoBook ro'yxatdan o'tish havolasi noto'g'ri. Iltimos, sayt orqali yangi havola oling.")
        return
    try:
        linked = link_telegram_account(payload, update.effective_user.id if update.effective_user else 0, update.effective_user.username if update.effective_user else "")
    except Exception as exc:
        logger.warning("Telegram account link failed (%s).", type(exc).__name__)
        await _reply_error(update, "Havola yaroqsiz yoki muddati tugagan. AvoBook saytiga qaytib yangi tasdiqlashni boshlang.")
        return

    code = linked.get("code")
    if code:
        text = (
            f"Assalomu alaykum! AvoBook ro‘yxatdan o‘tishni tasdiqlash kodi: {code}.\n\n"
            "Kod 5 daqiqa davomida amal qiladi. Uni AvoBook saytiga kiriting. "
            "Ushbu kodni boshqa odamlarga bermang."
        )
        await _reply_error(update, text)
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
    await _reply_error(update, text)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    await _reply_error(update, "Tasdiqlash bekor qilindi. AvoBook saytiga qaytib, qayta boshlashingiz mumkin.")
