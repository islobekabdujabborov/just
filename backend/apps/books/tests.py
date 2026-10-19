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
from apps.interactions.models import Like, Save
from apps.notifications.models import Notification
from apps.library.models import ListeningProgress
from .models import Review

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


class BookReviewApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="book-owner",
            email="owner@example.uz",
            password="strong-pass-123",
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.uz",
            password="strong-pass-123",
        )
        self.other_reviewer = User.objects.create_user(
            username="other-reviewer",
            email="other@example.uz",
            password="strong-pass-123",
        )
        self.author = Author.objects.create(name="Review Author")
        self.genre, _ = Genre.objects.get_or_create(name="Review Genre", defaults={"slug": "review-genre"})
        self.book = Book.objects.create(
            title="Review Book",
            author=self.author,
            genre=self.genre,
            owner=self.owner,
            rating=0,
        )
        self.url = f"/api/books/{self.book.id}/reviews/"
        self.client.force_authenticate(self.reviewer)

    def test_reviews_are_public_and_include_review_author(self):
        review = Review.objects.create(user=self.reviewer, book=self.book, rating=4, text="Yaxshi kitob.")
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], review.id)
        self.assertEqual(response.data["results"][0]["user_name"], self.reviewer.username)
        self.assertFalse(response.data["results"][0]["is_mine"])

    def test_authenticated_user_can_create_review_and_notify_book_owner(self):
        response = self.client.post(self.url, {"rating": 5, "text": "Juda yaxshi."}, format="json")

        self.assertEqual(response.status_code, 201)
        review = Review.objects.get(id=response.data["id"])
        self.assertEqual(review.user, self.reviewer)
        self.assertEqual(review.book, self.book)
        self.book.refresh_from_db()
        self.assertEqual(str(self.book.rating), "5.0")
        notification = Notification.objects.get(recipient=self.owner, type="review")
        self.assertEqual(notification.actor, self.reviewer)

    def test_review_creation_respects_notification_preferences(self):
        self.owner.notification_preferences = {"likeComments": False}
        self.owner.save(update_fields=["notification_preferences"])

        response = self.client.post(self.url, {"rating": 3, "text": ""}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertFalse(Notification.objects.filter(recipient=self.owner, type="review").exists())

    def test_review_owner_can_update_and_delete_and_rating_stays_synchronized(self):
        review = Review.objects.create(user=self.reviewer, book=self.book, rating=3, text="O'rtacha.")
        other_review = Review.objects.create(user=self.other_reviewer, book=self.book, rating=5)
        self.book.rating = 4
        self.book.save(update_fields=["rating"])

        update_response = self.client.patch(
            f"/api/reviews/{review.id}/",
            {"rating": 4, "text": "Yaxshi."},
            format="json",
        )
        self.book.refresh_from_db()
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(str(self.book.rating), "4.5")

        self.client.force_authenticate(self.other_reviewer)
        delete_response = self.client.delete(f"/api/reviews/{other_review.id}/")
        self.book.refresh_from_db()
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(str(self.book.rating), "4.0")

        self.client.force_authenticate(self.reviewer)
        final_delete_response = self.client.delete(f"/api/reviews/{review.id}/")
        self.book.refresh_from_db()
        self.assertEqual(final_delete_response.status_code, 204)
        self.assertEqual(str(self.book.rating), "0.0")

    def test_non_owner_cannot_update_or_delete_review(self):
        review = Review.objects.create(user=self.other_reviewer, book=self.book, rating=4)

        update_response = self.client.patch(f"/api/reviews/{review.id}/", {"rating": 1}, format="json")
        delete_response = self.client.delete(f"/api/reviews/{review.id}/")

        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Review.objects.filter(id=review.id).exists())

    def test_user_can_only_review_a_book_once(self):
        Review.objects.create(user=self.reviewer, book=self.book, rating=4)

        response = self.client.post(self.url, {"rating": 5, "text": "Ikkinchi sharh."}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.filter(user=self.reviewer, book=self.book).count(), 1)

    def test_invalid_rating_and_long_review_are_rejected(self):
        for payload in (
            {"rating": 0},
            {"rating": 6},
            {"rating": 5, "text": "x" * 2001},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, 400)

    def test_anonymous_user_cannot_create_review(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, {"rating": 5}, format="json")

        self.assertEqual(response.status_code, 401)


class RecommendationsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recommendation-reader",
            email="recommendation-reader@example.com",
            password="strong-pass-123",
        )
        self.author = Author.objects.create(name="Recommendation Author")
        self.liked_genre = Genre.objects.create(name="Liked Genre", slug="liked-genre")
        self.saved_genre = Genre.objects.create(name="Saved Genre", slug="saved-genre")
        self.listened_genre = Genre.objects.create(name="Listened Genre", slug="listened-genre")
        self.other_genre = Genre.objects.create(name="Other Genre", slug="other-genre")
        self.liked_book = Book.objects.create(
            title="Liked history",
            author=self.author,
            genre=self.liked_genre,
            rating=2,
        )
        self.saved_book = Book.objects.create(
            title="Saved history",
            author=self.author,
            genre=self.saved_genre,
            rating=2,
        )
        self.listened_book = Book.objects.create(
            title="Listened history",
            author=self.author,
            genre=self.listened_genre,
            rating=2,
        )
        self.liked_recommendation = Book.objects.create(
            title="Liked genre recommendation",
            author=self.author,
            genre=self.liked_genre,
            rating=3,
        )
        self.saved_recommendation = Book.objects.create(
            title="Saved genre recommendation",
            author=self.author,
            genre=self.saved_genre,
            rating=5,
        )
        self.listened_recommendation = Book.objects.create(
            title="Listened genre recommendation",
            author=self.author,
            genre=self.listened_genre,
            rating=5,
        )
        self.other_recommendation = Book.objects.create(
            title="Other genre recommendation",
            author=self.author,
            genre=self.other_genre,
            rating=5,
        )

    def test_authenticated_recommendations_rank_preferred_genres_and_exclude_history(self):
        Like.objects.create(user=self.user, book=self.liked_book)
        Save.objects.create(user=self.user, book=self.saved_book)
        audiobook = Audiobook.objects.create(book=self.listened_book)
        ListeningProgress.objects.create(user=self.user, audiobook=audiobook, position=20)
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        recommended_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(
            recommended_ids.index(self.liked_recommendation.id),
            recommended_ids.index(self.saved_recommendation.id),
        )
        self.assertLess(
            recommended_ids.index(self.saved_recommendation.id),
            recommended_ids.index(self.listened_recommendation.id),
        )
        self.assertNotIn(self.listened_book.id, recommended_ids)

    def test_new_user_and_anonymous_user_get_top_rated_books(self):
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)
        new_user_response = self.client.get("/api/recommendations/")
        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get("/api/recommendations/")

        for response in (new_user_response, anonymous_response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data["results"][0]["id"],
                self.other_recommendation.id,
            )

    def test_recommendations_are_paginated(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertIn("next", response.data)