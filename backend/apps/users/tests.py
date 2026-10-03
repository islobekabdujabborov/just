import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.reels.models import Reel
from .models import Follow, User


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

    def test_registration_rejects_common_password(self):
        response = self.client.post("/api/auth/register/", {
            "username": "new-reader",
            "email": "new-reader@example.com",
            "password": "12345678",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_registration_rejects_case_insensitive_duplicate_identity(self):
        response = self.client.post("/api/auth/register/", {
            "username": "CREATOR",
            "email": "CREATOR@example.com",
            "password": "different-secure-phrase-92",
        }, format="json")

        self.assertEqual(response.status_code, 400)

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