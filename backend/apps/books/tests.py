import tempfile
from io import BytesIO, StringIO
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase
from apps.users.models import User
from apps.books.models import Author, Book, Genre
from apps.reels.models import Reel
from apps.audiobooks.models import Audiobook
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

    def test_book_cover_upload_is_saved_and_returned_as_a_media_url(self):
        image = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(image, format="PNG")
        self.client.force_authenticate(self.user)
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post("/api/books/", {
                "title": "Muqovali asar",
                "author_name": "Yangi muallif",
                "genre": "Roman",
                "cover": SimpleUploadedFile("cover.png", image.getvalue(), content_type="image/png"),
            }, format="multipart")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["cover"].endswith("/media/books/cover.png"))

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

    def test_only_audiobook_owner_can_create_chapters(self):
        other_user = User.objects.create_user(username="other", email="other@example.uz", password="strong-pass-123")
        other_author = Author.objects.create(name="Other author")
        other_book = Book.objects.create(title="Other book", author=other_author, genre=self.genre, owner=other_user)
        audiobook = Audiobook.objects.create(book=other_book, created_by=other_user)
        self.client.force_authenticate(self.user)

        response = self.client.post(f"/api/audiobooks/{audiobook.id}/chapters/", {"title": "Unauthorized chapter"}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_invalid_listening_progress_returns_client_error(self):
        audiobook = Audiobook.objects.create(book=self.book, created_by=self.user)
        self.client.force_authenticate(self.user)

        response = self.client.post(f"/api/audiobooks/{audiobook.id}/progress/", {
            "position": "not-a-number",
            "percentage": 140,
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_seeded_demo_accounts_cannot_use_a_shared_password(self):
        call_command("seed_data", stdout=StringIO())

        seeded_user = User.objects.get(username="sardor_ovoz")
        self.assertFalse(seeded_user.has_usable_password())

    def test_reel_like_is_idempotent(self):
        reel = Reel.objects.create(author=self.user, book=self.book, caption="Demo reel")
        self.client.force_authenticate(self.user)
        first = self.client.post(f"/api/reels/{reel.id}/like/")
        second = self.client.post(f"/api/reels/{reel.id}/like/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.data["likes_count"], 1)
        self.assertEqual(Like.objects.filter(user=self.user, reel=reel).count(), 1)