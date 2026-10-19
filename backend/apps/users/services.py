import hashlib
import os
import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.users.models import TelegramVerification, User


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def get_pending_registration(request):
    pending = request.session.get("pending_registration") or {}
    if not isinstance(pending, dict):
        return {}
    return pending


def next_verification_session_ttl() -> timedelta:
    return timedelta(seconds=getattr(settings, "TELEGRAM_VERIFICATION_SESSION_TTL", 900))


def next_code_ttl() -> timedelta:
    return timedelta(seconds=getattr(settings, "TELEGRAM_VERIFICATION_CODE_TTL", 300))


def next_resend_cooldown() -> timedelta:
    return timedelta(seconds=getattr(settings, "TELEGRAM_VERIFICATION_RESEND_COOLDOWN", 60))


def next_max_attempts() -> int:
    return int(getattr(settings, "TELEGRAM_VERIFICATION_MAX_ATTEMPTS", 5))


def next_max_resends() -> int:
    return int(getattr(settings, "TELEGRAM_VERIFICATION_MAX_RESENDS", 3))


def verification_error(detail: str):
    raise ValidationError(detail)


def build_telegram_deep_link(payload: str) -> str:
    username = (getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "").lstrip("@")
    if not username:
        raise RuntimeError("TELEGRAM_BOT_USERNAME is not configured.")
    return f"https://t.me/{username}?start={payload}"


def create_telegram_verification(request, username: str, email: str, password: str, password_confirmation: str | None = None):
    username = (username or "").strip()
    email = (email or "").strip().lower()
    if not username or not email or not password:
        verification_error("Barcha maydonlarni to'ldiring.")
    if password_confirmation is not None and password != password_confirmation:
        verification_error("Parollar mos kelmadi.")
    if User.objects.filter(username__iexact=username).exists():
        verification_error("Bu foydalanuvchi nomi band.")
    if User.objects.filter(email__iexact=email).exists():
        verification_error("Bu email allaqachon ro'yxatdan o'tgan.")
    user = User(username=username, email=email)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        verification_error(exc.messages[0] if exc.messages else "Parol noto'g'ri.")

    verification_token = secrets.token_urlsafe(32)
    payload = secrets.token_urlsafe(32)
    expires_at = timezone.now() + next_verification_session_ttl()

    verification = TelegramVerification.objects.create(
        session_token_hash=hash_value(verification_token),
        start_payload_hash=hash_value(payload),
        username=username,
        email=email,
        password_hash=make_password(password),
        status=TelegramVerification.STATUS_PENDING,
        expires_at=expires_at,
    )

    request.session["pending_registration"] = {"username": username, "email": email}
    request.session["telegram_verification_token"] = verification_token
    request.session.modified = True

    return {
        "verification_token": verification_token,
        "deep_link": build_telegram_deep_link(payload),
        "expires_at": expires_at.isoformat(),
        "verification_id": verification.id,
    }


def get_verification_by_token(token: str | None):
    if not token:
        return None
    return TelegramVerification.objects.filter(session_token_hash=hash_value(token)).first()


def validate_verification_token(request, token: str | None):
    if not token:
        verification_error("Tasdiqlash sessiyasi topilmadi.")
    verification = get_verification_by_token(token)
    if not verification:
        verification_error("Tasdiqlash sessiyasi yaroqsiz.")
    session_token = request.session.get("telegram_verification_token")
    if session_token and session_token != token:
        verification_error("Tasdiqlash sessiyasi mos kelmadi.")
    return verification


def get_verification_status(request, token: str | None):
    verification = validate_verification_token(request, token)
    return {
        "status": verification.status,
        "telegram_linked": bool(verification.telegram_user_id),
        "verified": verification.status == TelegramVerification.STATUS_VERIFIED,
        "expired": verification.expires_at <= timezone.now() or verification.status in {TelegramVerification.STATUS_CANCELLED, TelegramVerification.STATUS_EXPIRED},
    }


def _mark_session_expired(verification):
    if verification.status not in {TelegramVerification.STATUS_VERIFIED, TelegramVerification.STATUS_CANCELLED}:
        verification.status = TelegramVerification.STATUS_EXPIRED
        verification.save(update_fields=["status", "updated_at"])


def _generate_new_code(verification):
    code = generate_code()
    verification.code_hash = hash_value(code)
    verification.code_expires_at = timezone.now() + next_code_ttl()
    verification.code_used_at = None
    verification.attempts = 0
    verification.save(update_fields=["code_hash", "code_expires_at", "code_used_at", "attempts", "updated_at"])
    return code


def link_telegram_account(payload: str, telegram_user_id: int, telegram_username: str | None = None):
    payload_hash = hash_value(payload)
    error_message = None
    verification = None
    code = None
    with transaction.atomic():
        verification = TelegramVerification.objects.select_for_update().filter(start_payload_hash=payload_hash).first()
        if not verification:
            error_message = "Telegram havolasi yaroqsiz yoki muddati tugagan."
        elif verification.expires_at <= timezone.now():
            verification.status = TelegramVerification.STATUS_EXPIRED
            verification.save(update_fields=["status", "updated_at"])
            error_message = "Tasdiqlash sessiyasi muddati tugagan."
        elif verification.status in {TelegramVerification.STATUS_VERIFIED, TelegramVerification.STATUS_CANCELLED}:
            error_message = "Tasdiqlash allaqachon yakunlangan."
        else:
            existing = TelegramVerification.objects.filter(
                telegram_user_id=telegram_user_id,
                status__in={TelegramVerification.STATUS_PENDING, TelegramVerification.STATUS_LINKED},
            ).exclude(pk=verification.pk).first()
            if existing is not None:
                error_message = "Bu Telegram akkaunti boshqa tasdiqlash sessiyasiga bog'langan."
            elif verification.telegram_user_id and verification.telegram_user_id != telegram_user_id:
                error_message = "Bu Telegram akkaunti ushbu sessiya uchun mos kelmayapti."
            else:
                if verification.telegram_user_id == telegram_user_id and verification.code_hash and verification.code_expires_at and verification.code_expires_at > timezone.now() and not verification.code_used_at:
                    code = None
                else:
                    code = _generate_new_code(verification)
                verification.telegram_user_id = telegram_user_id
                verification.telegram_username = (telegram_username or "")[:255]
                verification.status = TelegramVerification.STATUS_LINKED
                verification.save(update_fields=["telegram_user_id", "telegram_username", "status", "updated_at", "code_hash", "code_expires_at", "code_used_at", "attempts"])
                verification = verification
    if error_message:
        verification_error(error_message)
    return {"verification_id": verification.id, "status": verification.status, "code": code if code is not None else None}


def verify_registration_code(request, token: str | None, code: str | None):
    if not token or not code:
        verification_error("Kod kiritilmadi.")

    error_message = None
    verification = None
    with transaction.atomic():
        verification = TelegramVerification.objects.select_for_update().filter(session_token_hash=hash_value(token)).first()
        if not verification:
            error_message = "Tasdiqlash sessiyasi topilmadi."
        elif verification.expires_at <= timezone.now() and verification.status not in {TelegramVerification.STATUS_VERIFIED, TelegramVerification.STATUS_CANCELLED}:
            verification.status = TelegramVerification.STATUS_EXPIRED
            verification.save(update_fields=["status", "updated_at"])
            error_message = "Tasdiqlash kodi muddati tugagan."
        elif verification.status in {TelegramVerification.STATUS_CANCELLED, TelegramVerification.STATUS_EXPIRED}:
            error_message = "Tasdiqlash sessiyasi yaroqsiz."
        elif verification.status == TelegramVerification.STATUS_VERIFIED:
            error_message = "Tasdiqlash allaqachon yakunlangan."
        elif not verification.telegram_user_id:
            error_message = "Telegram akkaunti hali bog'lanmagan."
        elif verification.code_hash and verification.code_expires_at and verification.code_expires_at <= timezone.now():
            verification.status = TelegramVerification.STATUS_EXPIRED
            verification.code_used_at = timezone.now()
            verification.save(update_fields=["status", "code_used_at", "updated_at"])
            error_message = "Tasdiqlash kodi muddati tugagan."
        elif verification.attempts >= next_max_attempts():
            verification.status = TelegramVerification.STATUS_EXPIRED
            verification.save(update_fields=["status", "updated_at"])
            error_message = "Kodni urinishlar limiti tugadi."
        elif not verification.code_matches(str(code)):
            verification.attempts += 1
            verification.save(update_fields=["attempts", "updated_at"])
            error_message = "Kod noto'g'ri."
        elif verification.code_used_at:
            error_message = "Kod allaqachon ishlatilgan."
        elif verification.code_hash and verification.code_expires_at and verification.code_expires_at <= timezone.now():
            error_message = "Tasdiqlash kodi muddati tugagan."
        else:
            verification.status = TelegramVerification.STATUS_VERIFIED
            verification.verified_at = timezone.now()
            verification.code_used_at = timezone.now()
            verification.save(update_fields=["status", "verified_at", "code_used_at", "updated_at"])

    if error_message:
        verification_error(error_message)

    if User.objects.filter(username__iexact=verification.username).exists() or User.objects.filter(email__iexact=verification.email).exists():
        request.session.pop("pending_registration", None)
        request.session.pop("telegram_verification_token", None)
        request.session.modified = True
        verification_error("Bu foydalanuvchi allaqachon ro'yxatdan o'tgan.")

    user = User(username=verification.username, email=verification.email, password=verification.password_hash)
    user.save()
    request.session.pop("pending_registration", None)
    request.session.pop("telegram_verification_token", None)
    request.session.modified = True

    from rest_framework_simplejwt.tokens import RefreshToken

    refresh_token = RefreshToken.for_user(user)
    return {
        "status": "verified",
        "detail": "Tasdiqlash muvaffaqiyatli yakunlandi.",
        "access": str(refresh_token.access_token),
        "refresh": str(refresh_token),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }


def resend_verification_code(request, token: str | None):
    verification = validate_verification_token(request, token)
    if verification.status in {TelegramVerification.STATUS_CANCELLED, TelegramVerification.STATUS_EXPIRED, TelegramVerification.STATUS_VERIFIED}:
        verification_error("Tasdiqlash sessiyasi yopiq.")
    if not verification.telegram_user_id:
        verification_error("Telegram akkaunti hali bog'lanmagan.")
    if verification.resend_count >= next_max_resends():
        verification_error("Kodni qayta yuborish limiti tugadi.")
    now = timezone.now()
    if verification.last_resend_at and now - verification.last_resend_at < next_resend_cooldown():
        verification_error("Kodni qayta yuborish uchun biroz kuting.")
    code = _generate_new_code(verification)
    verification.resend_count += 1
    verification.last_resend_at = now
    verification.save(update_fields=["resend_count", "last_resend_at", "code_hash", "code_expires_at", "attempts", "code_used_at", "updated_at"])
    return {"status": "resent", "code": code}


def cancel_verification(request, token: str | None):
    verification = validate_verification_token(request, token)
    verification.status = TelegramVerification.STATUS_CANCELLED
    verification.save(update_fields=["status", "updated_at"])
    request.session.pop("pending_registration", None)
    request.session.pop("telegram_verification_token", None)
    request.session.modified = True
    return {"status": "cancelled"}


def cleanup_expired_verifications():
    now = timezone.now()
    TelegramVerification.objects.filter(expires_at__lt=now, status__in=[TelegramVerification.STATUS_PENDING, TelegramVerification.STATUS_LINKED]).update(status=TelegramVerification.STATUS_EXPIRED)
    TelegramVerification.objects.filter(code_expires_at__lt=now, status=TelegramVerification.STATUS_LINKED).update(status=TelegramVerification.STATUS_EXPIRED)
