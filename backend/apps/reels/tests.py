from datetime import timedelta
import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.books.models import Author, Book, Genre
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
