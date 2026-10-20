from datetime import timedelta
import os
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.books.models import Author, Book, Genre
from apps.audiobooks.models import Audiobook, Chapter
from apps.comments.models import Comment
from apps.interactions.models import Like, Save
from apps.users.models import Follow, User
from .models import Reel


class ReelDeleteApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="reel-owner",
            email="reel-owner@example.com",
            password="secure-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="other-reader",
            email="other-reader@example.com",
            password="secure-pass-123",
        )
        self.reel = Reel.objects.create(author=self.owner, caption="Delete this reel")
        self.url = f"/api/reels/{self.reel.id}/"

    def test_reel_owner_can_delete_reel_and_video_file(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            reel = Reel.objects.create(
                author=self.owner,
                caption="Reel with video",
                video=SimpleUploadedFile("sample.mp4", b"video bytes", content_type="video/mp4"),
            )
            video_path = reel.video.path
            self.client.force_authenticate(self.owner)

            response = self.client.delete(f"/api/reels/{reel.id}/")

            self.assertEqual(response.status_code, 204)
            self.assertFalse(Reel.objects.filter(pk=reel.pk).exists())
            self.assertFalse(os.path.exists(video_path))

    def test_replacing_reel_video_removes_previous_file(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            reel = Reel.objects.create(
                author=self.owner,
                video=SimpleUploadedFile("first.mp4", b"first video", content_type="video/mp4"),
            )
            previous_path = reel.video.path

            reel.video = SimpleUploadedFile("second.mp4", b"second video", content_type="video/mp4")
            reel.save()

            self.assertFalse(os.path.exists(previous_path))
            self.assertTrue(os.path.exists(reel.video.path))

    def test_other_user_cannot_delete_reel(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Reel.objects.filter(pk=self.reel.pk).exists())

    def test_anonymous_user_cannot_delete_reel(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertTrue(Reel.objects.filter(pk=self.reel.pk).exists())


class FollowingReelFeedApiTests(APITestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="strong-pass-123",
        )
        self.followed = User.objects.create_user(
            username="followed",
            email="followed@example.com",
            password="strong-pass-123",
        )
        self.unfollowed = User.objects.create_user(
            username="unfollowed",
            email="unfollowed@example.com",
            password="strong-pass-123",
        )
        self.author = Author.objects.create(name="Feed Author")
        self.genre, _ = Genre.objects.get_or_create(name="Feed Genre", defaults={"slug": "feed-genre"})
        self.book = Book.objects.create(title="Feed Book", author=self.author, genre=self.genre, owner=self.followed)
        Follow.objects.create(follower=self.viewer, followed=self.followed)
        self.followed_reel = Reel.objects.create(author=self.followed, book=self.book, caption="Followed reel")
        Reel.objects.create(author=self.unfollowed, book=self.book, caption="Unfollowed reel")
        self.client.force_authenticate(self.viewer)

    def test_feed_contains_only_followed_users_newest_first(self):
        older_reel = Reel.objects.create(author=self.followed, book=self.book, caption="Older followed reel")
        older_reel.created_at = timezone.now() - timedelta(days=1)
        older_reel.save(update_fields=["created_at"])

        response = self.client.get("/api/reels/feed/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.followed_reel.id, older_reel.id],
        )

    def test_feed_returns_correct_counts_and_viewer_interaction_flags(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="strong-pass-123",
        )
        Like.objects.create(user=self.viewer, reel=self.followed_reel)
        Like.objects.create(user=other_user, reel=self.followed_reel)
        Save.objects.create(user=self.viewer, reel=self.followed_reel)
        Save.objects.create(user=other_user, reel=self.followed_reel)
        Comment.objects.create(user=other_user, reel=self.followed_reel, text="First comment")
        Comment.objects.create(user=self.followed, reel=self.followed_reel, text="Second comment")

        response = self.client.get("/api/reels/feed/")

        self.assertEqual(response.status_code, 200)
        reel_data = next(item for item in response.data["results"] if item["id"] == self.followed_reel.id)
        self.assertEqual(reel_data["likes_count"], 2)
        self.assertEqual(reel_data["comments_count"], 2)
        self.assertEqual(reel_data["saves_count"], 2)
        self.assertTrue(reel_data["is_liked"])
        self.assertTrue(reel_data["is_saved"])

    def test_feed_is_empty_when_user_follows_nobody(self):
        Follow.objects.filter(follower=self.viewer).delete()

        response = self.client.get("/api/reels/feed/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_feed_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/reels/feed/")

        self.assertEqual(response.status_code, 401)


class ReelComposeApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="compose-owner",
            email="compose-owner@example.com",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="compose-other",
            email="compose-other@example.com",
            password="test-password",
        )
        self.author = Author.objects.create(name="Compose Author")
        self.genre = Genre.objects.create(name="Compose Genre", slug="compose-genre")
        self.client.force_authenticate(self.owner)

    def video(self):
        return SimpleUploadedFile("clip.mp4", b"video content", content_type="video/mp4")

    def audio(self, name="chapter.mp3"):
        return SimpleUploadedFile(name, b"audio content", content_type="audio/mpeg")

    @patch("apps.reels.views._ffprobe_duration", return_value=12)
    def test_compose_creates_book_audiobook_chapter_and_reel(self, _probe):
        response = self.client.post(
            "/api/reels/compose/",
            {
                "video": self.video(),
                "title": "Ajoyib kitob",
                "author_name": "Compose Author",
                "genre": "Compose Genre",
                "audio_files": self.audio(),
                "chapter_titles": "1-bob",
                "chapter_free_preview": "true",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Audiobook.objects.count(), 1)
        self.assertEqual(Chapter.objects.count(), 1)
        self.assertEqual(response.data["book"]["chapter_count"], 1)
        self.assertTrue(response.data["book"]["has_audio"])
        self.assertEqual(response.data["book"]["audiobook_id"], Audiobook.objects.get().id)
        self.assertEqual(response.data["book"]["access"], Audiobook.ACCESS_FREE)
        chapter = Chapter.objects.get()
        self.assertEqual(chapter.title, "1-bob")
        self.assertEqual(chapter.duration, 12)
        self.assertTrue(chapter.is_free_preview)

    @patch("apps.reels.views._ffprobe_duration", return_value=12)
    def test_compose_adds_multiple_chapters_with_premium_preview(self, _probe):
        response = self.client.post(
            "/api/reels/compose/",
            {
                "video": self.video(),
                "title": "Premium kitob",
                "author_name": "Compose Author",
                "genre": "Compose Genre",
                "access": Audiobook.ACCESS_PREMIUM,
                "audio_files": [self.audio("first.mp3"), self.audio("second.mp3")],
                "chapter_titles": ["Kirish", "Davomi"],
                "chapter_free_preview": ["true", "false"],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["book"]["chapter_count"], 2)
        self.assertEqual(response.data["book"]["access"], Audiobook.ACCESS_PREMIUM)
        self.assertFalse(response.data["book"]["is_locked"])
        chapters = list(Chapter.objects.order_by("order"))
        self.assertEqual([chapter.order for chapter in chapters], [1, 2])
        self.assertEqual([chapter.is_free_preview for chapter in chapters], [True, False])
        self.assertEqual(Audiobook.objects.get().duration, 24)
        self.assertEqual(Book.objects.get().duration, 24)
        self.client.force_authenticate(user=None)
        feed_response = self.client.get("/api/reels/")
        self.assertTrue(feed_response.data["results"][0]["book"]["is_locked"])

    @patch("apps.reels.views._ffprobe_duration", return_value=0)
    def test_compose_reuses_existing_book_without_duplicate(self, _probe):
        book = Book.objects.create(title="Mavjud", author=self.author, genre=self.genre, owner=self.owner)

        response = self.client.post(
            "/api/reels/compose/",
            {
                "video": self.video(),
                "book_id": str(book.id),
                "audio_files": self.audio(),
                "chapter_titles": "Bob",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Audiobook.objects.get().created_by, self.owner)

    @patch("apps.reels.views._ffprobe_duration", return_value=0)
    def test_compose_appends_chapter_to_users_existing_audiobook(self, _probe):
        book = Book.objects.create(title="Mavjud", author=self.author, genre=self.genre, owner=self.owner)
        audiobook = Audiobook.objects.create(book=book, created_by=self.owner)
        Chapter.objects.create(audiobook=audiobook, title="Avvalgi bob", order=1)

        response = self.client.post(
            "/api/reels/compose/",
            {
                "video": self.video(),
                "book_id": str(book.id),
                "audio_files": self.audio(),
                "chapter_titles": "Yangi bob",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Audiobook.objects.count(), 1)
        self.assertEqual(Chapter.objects.count(), 2)
        self.assertEqual(
            list(Chapter.objects.order_by("order").values_list("title", "order")),
            [("Avvalgi bob", 1), ("Yangi bob", 2)],
        )

    def test_non_owner_cannot_attach_audio_to_another_users_book(self):
        book = Book.objects.create(title="Boshqa", author=self.author, genre=self.genre, owner=self.other_user)

        response = self.client.post(
            "/api/reels/compose/",
            {
                "video": self.video(),
                "book_id": str(book.id),
                "audio_files": self.audio(),
                "chapter_titles": "Bob",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reel.objects.count(), 0)
        self.assertEqual(Audiobook.objects.count(), 0)

    def test_invalid_audio_rolls_back_without_saved_files(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post(
                "/api/reels/compose/",
                {
                    "video": self.video(),
                    "title": "Yangi kitob",
                    "author_name": "Compose Author",
                    "genre": "Compose Genre",
                    "audio_files": SimpleUploadedFile("wrong.txt", b"not audio"),
                },
                format="multipart",
            )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(Book.objects.count(), 0)
            self.assertEqual(Reel.objects.count(), 0)
            self.assertEqual(Audiobook.objects.count(), 0)
            self.assertEqual(Chapter.objects.count(), 0)
            self.assertEqual(os.listdir(media_dir), [])

    def test_compose_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post("/api/reels/compose/", {"video": self.video()}, format="multipart")

        self.assertEqual(response.status_code, 401)

    @patch("apps.reels.views._ffprobe_duration", return_value=0)
    def test_composed_premium_audio_remains_blocked_from_public_media(self, _probe):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post(
                "/api/reels/compose/",
                {
                    "video": self.video(),
                    "title": "Premium kitob",
                    "author_name": "Compose Author",
                    "genre": "Compose Genre",
                    "access": Audiobook.ACCESS_PREMIUM,
                    "audio_files": self.audio(),
                    "chapter_titles": "Maxfiy bob",
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 201, response.data)
            chapter = Chapter.objects.get()
            media_response = self.client.get(chapter.audio_file.url)
            if media_response.streaming:
                b"".join(media_response.streaming_content)
            media_response.close()
            self.assertEqual(media_response.status_code, 403)
