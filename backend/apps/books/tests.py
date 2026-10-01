import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from apps.users.models import User
from apps.books.models import Author, Book, Genre
from apps.reels.models import Reel
from apps.interactions.models import Like

class AvoBookApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", email="tester@example.uz", password="strong-pass-123")
        self.author = Author.objects.create(name="Abdulla Qodiriy")
        self.genre, _ = Genre.objects.get_or_create(name="Roman", defaults={"slug": "roman"})
        self.book = Book.objects.create(title="O'tkan kunlar", author=self.author, genre=self.genre, rating=4.9, duration=45600, owner=self.user)

    def test_registration_returns_jwt_and_user(self):
        response = self.client.post("/api/auth/register/", {"username": "new-reader", "email": "reader@example.uz", "password": "strong-pass-123"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "new-reader")

    def test_book_payload_has_ui_compatibility_fields(self):
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, 200)
        payload = response.data["results"][0]
        self.assertEqual(payload["t"], "O'tkan kunlar")
        self.assertEqual(payload["a"], "Abdulla Qodiriy")
        self.assertEqual(payload["g"], "Roman")
        self.assertEqual(payload["d"], "12s 40d")

    def test_book_can_be_created_with_a_default_genre(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/books/", {
            "title": "Yangi asar",
            "author_name": "Yangi muallif",
            "genre": "Ta'lim",
            "language": "uz",
        }, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["g"], "Ta'lim")

    def test_reel_can_be_created_with_a_video(self):
        self.client.force_authenticate(self.user)
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post("/api/reels/", {
                "book_id": self.book.id,
                "caption": "Yangi reel",
                "video": SimpleUploadedFile("reel.mp4", b"video", content_type="video/mp4"),
            }, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["caption"], "Yangi reel")

    def test_reel_like_is_idempotent(self):
        reel = Reel.objects.create(author=self.user, book=self.book, caption="Demo reel")
        self.client.force_authenticate(self.user)
        first = self.client.post(f"/api/reels/{reel.id}/like/")
        second = self.client.post(f"/api/reels/{reel.id}/like/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.data["likes_count"], 1)
        self.assertEqual(Like.objects.filter(user=self.user, reel=reel).count(), 1)