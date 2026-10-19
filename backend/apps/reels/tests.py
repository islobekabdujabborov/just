from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.books.models import Author, Book, Genre
from apps.comments.models import Comment
from apps.interactions.models import Like, Save
from apps.users.models import Follow, User
from .models import Reel


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
