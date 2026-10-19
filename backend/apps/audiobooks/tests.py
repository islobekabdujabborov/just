import tempfile
import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.books.models import Author, Book, Genre
from apps.users.models import Subscription, User
from .models import Audiobook, Bookmark, Chapter


class BookmarkApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="strong-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="another-reader",
            email="another-reader@example.com",
            password="strong-pass-123",
        )
        self.author = Author.objects.create(name="Audiobook Author")
        self.genre, _ = Genre.objects.get_or_create(name="Bookmark Genre", defaults={"slug": "bookmark-genre"})
        self.book = Book.objects.create(title="Bookmark Book", author=self.author, genre=self.genre, owner=self.user)
        self.audiobook = Audiobook.objects.create(book=self.book, created_by=self.user)
        self.chapter = Chapter.objects.create(audiobook=self.audiobook, title="Chapter One")
        self.other_audiobook = Audiobook.objects.create(book=self.book, created_by=self.user)
        self.other_chapter = Chapter.objects.create(audiobook=self.other_audiobook, title="Other Chapter")
        self.client.force_authenticate(self.user)

    def test_bookmark_list_contains_only_current_users_bookmarks(self):
        own_bookmark = Bookmark.objects.create(
            user=self.user,
            audiobook=self.audiobook,
            chapter=self.chapter,
            position=42,
        )
        Bookmark.objects.create(user=self.other_user, audiobook=self.audiobook, position=12)

        response = self.client.get(f"/api/audiobooks/{self.audiobook.id}/bookmarks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [own_bookmark.id])

    def test_authenticated_user_can_create_bookmark_with_note(self):
        response = self.client.post(
            f"/api/audiobooks/{self.audiobook.id}/bookmarks/",
            {"chapter": self.chapter.id, "position": 42, "note": "Muhim parcha"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        bookmark = Bookmark.objects.get(id=response.data["id"])
        self.assertEqual(bookmark.user, self.user)
        self.assertEqual(bookmark.audiobook, self.audiobook)
        self.assertEqual(bookmark.chapter, self.chapter)
        self.assertEqual(bookmark.note, "Muhim parcha")

    def test_bookmark_creation_rejects_negative_position_and_long_note(self):
        for payload in (
            {"position": -1},
            {"position": 0, "note": "x" * 501},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(
                    f"/api/audiobooks/{self.audiobook.id}/bookmarks/",
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

    def test_bookmark_rejects_chapter_from_another_audiobook(self):
        response = self.client.post(
            f"/api/audiobooks/{self.audiobook.id}/bookmarks/",
            {"chapter": self.other_chapter.id, "position": 0},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Bookmark.objects.exists())

    def test_owner_can_update_and_delete_bookmark(self):
        bookmark = Bookmark.objects.create(user=self.user, audiobook=self.audiobook, position=12)

        update_response = self.client.patch(
            f"/api/bookmarks/{bookmark.id}/",
            {"position": 25, "note": "Davom ettirish"},
            format="json",
        )
        delete_response = self.client.delete(f"/api/bookmarks/{bookmark.id}/")

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["position"], 25)
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_non_owner_cannot_update_or_delete_bookmark(self):
        bookmark = Bookmark.objects.create(user=self.other_user, audiobook=self.audiobook, position=12)

        update_response = self.client.patch(
            f"/api/bookmarks/{bookmark.id}/",
            {"position": 25},
            format="json",
        )
        delete_response = self.client.delete(f"/api/bookmarks/{bookmark.id}/")

        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Bookmark.objects.filter(id=bookmark.id).exists())

    def test_bookmark_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        list_response = self.client.get(f"/api/audiobooks/{self.audiobook.id}/bookmarks/")
        create_response = self.client.post(
            f"/api/audiobooks/{self.audiobook.id}/bookmarks/",
            {"position": 0},
            format="json",
        )

        self.assertEqual(list_response.status_code, 401)
        self.assertEqual(create_response.status_code, 401)


class PremiumAudiobookAccessTests(APITestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()
        self.owner = User.objects.create_user(
            username="audio-owner",
            email="audio-owner@example.com",
            password="strong-pass-123",
        )
        self.listener = User.objects.create_user(
            username="listener",
            email="listener@example.com",
            password="strong-pass-123",
        )
        self.staff = User.objects.create_user(
            username="audio-staff",
            email="audio-staff@example.com",
            password="strong-pass-123",
            is_staff=True,
        )
        author = Author.objects.create(name="Premium Audio Author")
        genre, _ = Genre.objects.get_or_create(name="Premium Audio Genre", defaults={"slug": "premium-audio-genre"})
        book = Book.objects.create(title="Premium Audio Book", author=author, genre=genre, owner=self.owner)
        self.audiobook = Audiobook.objects.create(
            book=book,
            created_by=self.owner,
            access=Audiobook.ACCESS_PREMIUM,
        )
        self.locked_chapter = Chapter.objects.create(
            audiobook=self.audiobook,
            title="Locked chapter",
            order=1,
            duration=120,
            audio_file=SimpleUploadedFile("locked.mp3", b"0123456789", content_type="audio/mpeg"),
        )
        self.preview_chapter = Chapter.objects.create(
            audiobook=self.audiobook,
            title="Free preview",
            order=2,
            duration=30,
            is_free_preview=True,
            audio_file=SimpleUploadedFile("preview.mp3", b"preview audio", content_type="audio/mpeg"),
        )
        free_book = Book.objects.create(title="Free Audio Book", author=author, genre=genre, owner=self.owner)
        self.free_audiobook = Audiobook.objects.create(book=free_book, created_by=self.owner)
        self.free_chapter = Chapter.objects.create(
            audiobook=self.free_audiobook,
            title="Free chapter",
            audio_file=SimpleUploadedFile("free.mp3", b"free audio", content_type="audio/mpeg"),
        )

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def test_chapter_list_hides_locked_audio_but_keeps_metadata_and_preview(self):
        response = self.client.get(f"/api/audiobooks/{self.audiobook.id}/chapters/")
        chapters = {item["id"]: item for item in response.data["results"]}

        locked = chapters[self.locked_chapter.id]
        preview = chapters[self.preview_chapter.id]
        self.assertTrue(locked["locked"])
        self.assertEqual(locked["title"], "Locked chapter")
        self.assertEqual(locked["order"], 1)
        self.assertEqual(locked["duration"], 120)
        self.assertIsNone(locked["audio_file"])
        self.assertIsNone(locked["audio_url"])
        self.assertFalse(preview["locked"])
        self.assertTrue(preview["is_free_preview"])
        self.assertIsNone(preview["audio_file"])

    def test_free_audiobook_access_is_unchanged(self):
        response = self.client.get(f"/api/audiobooks/{self.free_audiobook.id}/chapters/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["results"][0]["locked"])
        self.assertTrue(response.data["results"][0]["audio_url"].endswith("/media/chapters/free.mp3"))

    def test_locked_premium_chapter_requires_subscription(self):
        response = self.client.get(f"/api/chapters/{self.locked_chapter.id}/stream/")

        self.assertEqual(response.status_code, 403)

    def test_owner_staff_and_active_subscriber_can_access_premium_chapter(self):
        subscription = Subscription.objects.create(
            user=self.listener,
            plan=Subscription.PLAN_MONTHLY,
            status=Subscription.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )
        for user in (self.owner, self.staff, self.listener):
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                response = self.client.get(f"/api/chapters/{self.locked_chapter.id}/stream/")
                self.assertEqual(response.status_code, 200)
                self.assertIn("/media-protected/chapters/", response.data["url"])
        self.assertTrue(subscription.grants_access)

    def test_canceled_but_unexpired_subscription_can_stream(self):
        Subscription.objects.create(
            user=self.listener,
            plan=Subscription.PLAN_YEARLY,
            status=Subscription.STATUS_CANCELED,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(self.listener)

        response = self.client.get(f"/api/chapters/{self.locked_chapter.id}/stream/")

        self.assertEqual(response.status_code, 200)

    def test_expired_subscription_cannot_stream(self):
        Subscription.objects.create(
            user=self.listener,
            plan=Subscription.PLAN_MONTHLY,
            status=Subscription.STATUS_ACTIVE,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.client.force_authenticate(self.listener)

        response = self.client.get(f"/api/chapters/{self.locked_chapter.id}/stream/")

        self.assertEqual(response.status_code, 403)

    def test_signed_audio_url_supports_ranges_and_expires_after_ten_minutes(self):
        self.client.force_authenticate(self.owner)
        stream_response = self.client.get(f"/api/chapters/{self.locked_chapter.id}/stream/")
        stream_path = urlsplit(stream_response.data["url"]).path

        range_response = self.client.get(stream_path, HTTP_RANGE="bytes=2-5")
        self.assertEqual(range_response.status_code, 206)
        self.assertEqual(b"".join(range_response.streaming_content), b"2345")

        future_time = time.time() + 601
        with patch("django.core.signing.time.time", return_value=future_time):
            expired_response = self.client.get(stream_path)
        self.assertEqual(expired_response.status_code, 403)

    def test_direct_media_route_blocks_premium_audio_but_allows_preview(self):
        locked_response = self.client.get(self.locked_chapter.audio_file.url)
        preview_response = self.client.get(self.preview_chapter.audio_file.url)
        if preview_response.streaming:
            b"".join(preview_response.streaming_content)
        locked_response.close()
        preview_response.close()

        self.assertEqual(locked_response.status_code, 403)
        self.assertEqual(preview_response.status_code, 200)
