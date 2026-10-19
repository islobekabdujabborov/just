import tempfile
from io import BytesIO

from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.reels.models import Reel
from apps.users.models import TelegramVerification
from apps.users.services import link_telegram_account
from .models import Follow, Subscription, User


class UserProfileApiTests(APITestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="strong-pass-123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="strong-pass-123",
        )

    def test_profile_is_public_and_reports_follow_state(self):
        response = self.client.get("/api/users/creator/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "creator")
        self.assertFalse(response.data["is_following"])
        self.assertNotIn("email", response.data)

    def test_public_profile_includes_serialized_reels(self):
        Reel.objects.create(author=self.creator, caption="Profile reel")

        response = self.client.get("/api/users/creator/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reels"][0]["caption"], "Profile reel")
        self.assertNotIn("email", response.data["reels"][0]["author"])

    def test_private_current_user_endpoint_includes_email(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.viewer.email)

    def test_authenticated_user_can_upload_avatar(self):
        image = BytesIO()
        Image.new("RGB", (1, 1), color="black").save(image, format="PNG")
        self.client.force_authenticate(self.viewer)
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.patch("/api/auth/me/", {
                "avatar": SimpleUploadedFile("avatar.png", image.getvalue(), content_type="image/png"),
            }, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["avatar"].endswith("/media/avatars/avatar.png"))

    def test_current_user_keeps_notification_preferences_server_side(self):
        self.client.force_authenticate(self.viewer)

        response = self.client.patch("/api/auth/me/", {
            "notification_preferences": {"likeComments": False, "newFollowers": True, "newBooks": True, "privateAccount": False},
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["notification_preferences"]["likeComments"])
        self.assertTrue(response.data["notification_preferences"]["newFollowers"])

        fresh = self.client.get("/api/auth/me/")
        self.assertEqual(fresh.status_code, 200)
        self.assertFalse(fresh.data["notification_preferences"]["likeComments"])

    def test_direct_registration_endpoint_is_unavailable(self):
        response = self.client.post("/api/auth/register/", {
            "username": "new-reader",
            "email": "new-reader@example.com",
            "password": "12345678",
        }, format="json")

        self.assertEqual(response.status_code, 404)

    def test_direct_registration_endpoint_is_unavailable_for_duplicate_identity(self):
        response = self.client.post("/api/auth/register/", {
            "username": "CREATOR",
            "email": "CREATOR@example.com",
            "password": "different-secure-phrase-92",
        }, format="json")

        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_follow_and_unfollow(self):
        self.client.force_authenticate(self.viewer)
        path = "/api/users/creator/follow/"

        followed = self.client.post(path, {}, format="json")
        self.assertEqual(followed.status_code, 200)
        self.assertTrue(followed.data["is_following"])
        self.assertTrue(Follow.objects.filter(follower=self.viewer, followed=self.creator).exists())
        self.client.post(path, {}, format="json")
        self.assertEqual(Notification.objects.filter(recipient=self.creator, type="follow").count(), 1)

        profile = self.client.get("/api/users/creator/")
        self.assertTrue(profile.data["is_following"])

        unfollowed = self.client.delete(path)
        self.assertEqual(unfollowed.status_code, 200)
        self.assertFalse(unfollowed.data["is_following"])
        self.assertFalse(Follow.objects.filter(follower=self.viewer, followed=self.creator).exists())


@override_settings(TELEGRAM_BOT_USERNAME="sample_bot", TELEGRAM_BOT_TOKEN="test-bot-token")
class TelegramVerificationApiTests(APITestCase):
    def start_verification(self, username="telegram-user", email="telegram@example.com"):
        response = self.client.post("/api/auth/telegram/start/", {
            "username": username,
            "email": email,
            "password": "secure-pass-123",
            "confirmPassword": "secure-pass-123",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("verification_token", response.data)
        self.assertIn("deep_link", response.data)
        return response.data

    def test_successful_telegram_verification_registers_user(self):
        session_data = self.start_verification(username="telegram-user", email="telegram@example.com")
        payload = session_data["deep_link"].split("start=")[-1]
        result = link_telegram_account(payload, 987654321, "telegrambot")
        self.assertIsNotNone(result["code"])

        response = self.client.post("/api/auth/telegram/verify/", {
            "verification_token": session_data["verification_token"],
            "code": result["code"],
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "verified")
        self.assertTrue(User.objects.filter(username="telegram-user").exists())
        self.assertTrue(User.objects.filter(email="telegram@example.com").exists())

    def test_invalid_code_increments_attempts(self):
        session_data = self.start_verification(username="telegram-user-2", email="telegram2@example.com")
        payload = session_data["deep_link"].split("start=")[-1]
        link_telegram_account(payload, 111222333, "telegrambot")

        response = self.client.post("/api/auth/telegram/verify/", {
            "verification_token": session_data["verification_token"],
            "code": "000000",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        verification = TelegramVerification.objects.get(session_token_hash=TelegramVerification.hash_value(session_data["verification_token"]))
        self.assertEqual(verification.attempts, 1)

    def test_expired_code_is_rejected(self):
        session_data = self.start_verification(username="telegram-user-3", email="telegram3@example.com")
        payload = session_data["deep_link"].split("start=")[-1]
        result = link_telegram_account(payload, 222333444, "telegrambot")
        verification = TelegramVerification.objects.get(session_token_hash=TelegramVerification.hash_value(session_data["verification_token"]))
        verification.code_expires_at = timezone.now() - timedelta(minutes=1)
        verification.save(update_fields=["code_expires_at", "updated_at"])

        response = self.client.post("/api/auth/telegram/verify/", {
            "verification_token": session_data["verification_token"],
            "code": result["code"],
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_resend_is_rate_limited(self):
        session_data = self.start_verification(username="telegram-user-4", email="telegram4@example.com")
        payload = session_data["deep_link"].split("start=")[-1]
        link_telegram_account(payload, 333444555, "telegrambot")

        first = self.client.post("/api/auth/telegram/resend/", {"verification_token": session_data["verification_token"]}, format="json")
        second = self.client.post("/api/auth/telegram/resend/", {"verification_token": session_data["verification_token"]}, format="json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)


class SubscriptionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="strong-pass-123",
        )
        self.client.force_authenticate(self.user)

    def create_subscription(self, **overrides):
        defaults = {
            "user": self.user,
            "plan": Subscription.PLAN_MONTHLY,
            "status": Subscription.STATUS_ACTIVE,
            "expires_at": timezone.now() + timedelta(days=30),
        }
        defaults.update(overrides)
        return Subscription.objects.create(**defaults)

    def test_status_returns_current_subscription_access(self):
        subscription = self.create_subscription(provider="manual")

        response = self.client.get("/api/subscription/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["has_access"])
        self.assertEqual(response.data["subscription"]["plan"], subscription.plan)
        self.assertEqual(response.data["subscription"]["provider"], "manual")

    def test_cancellation_keeps_access_until_expiry_and_is_idempotent(self):
        subscription = self.create_subscription()

        first = self.client.post("/api/subscription/cancel/")
        second = self.client.post("/api/subscription/cancel/")
        subscription.refresh_from_db()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["status"], Subscription.STATUS_CANCELED)
        self.assertTrue(first.data["has_access"])
        self.assertEqual(second.status_code, 200)
        self.assertIsNotNone(subscription.canceled_at)
        self.assertTrue(subscription.grants_access)

    def test_expired_subscription_does_not_grant_access_or_cancel(self):
        subscription = self.create_subscription(expires_at=timezone.now() - timedelta(seconds=1))

        status_response = self.client.get("/api/subscription/")
        cancel_response = self.client.post("/api/subscription/cancel/")

        self.assertFalse(status_response.data["has_access"])
        self.assertEqual(cancel_response.status_code, 404)
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)

    def test_active_for_includes_unexpired_canceled_subscriptions(self):
        canceled = self.create_subscription(status=Subscription.STATUS_CANCELED)
        expired = self.create_subscription(
            user=User.objects.create_user(
                username="expired-subscriber",
                email="expired@example.com",
                password="strong-pass-123",
            ),
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertEqual(list(Subscription.objects.active_for(self.user)), [canceled])
        self.assertFalse(Subscription.objects.active_for(expired.user).exists())

    def test_only_one_active_subscription_per_user(self):
        self.create_subscription()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_subscription()

    def test_checkout_and_webhook_are_provider_agnostic_stubs(self):
        checkout = self.client.post("/api/payments/checkout/", {"plan": "monthly"}, format="json")
        webhook = self.client.post("/api/payments/payme/webhook/", {"event": "paid"}, format="json")

        self.assertEqual(checkout.status_code, 501)
        self.assertEqual(webhook.status_code, 501)

    def test_subscription_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        status_response = self.client.get("/api/subscription/")
        cancel_response = self.client.post("/api/subscription/cancel/")
        checkout_response = self.client.post("/api/payments/checkout/", {}, format="json")

        self.assertEqual(status_response.status_code, 401)
        self.assertEqual(cancel_response.status_code, 401)
        self.assertEqual(checkout_response.status_code, 401)