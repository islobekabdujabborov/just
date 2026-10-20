import os
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audiobooks.access import can_access_chapter
from apps.audiobooks.models import Audiobook, Bookmark, Chapter
from apps.books.models import Author, Book, Genre, Review
from apps.comments.models import Comment, CommentLike
from apps.interactions.models import Like, Save
from apps.reels.models import Reel
from apps.users.models import Follow, Subscription, User
from .models import AdminAuditLog


class AdminPanelUserApiTests(APITestCase):
    def setUp(self):
        self.normal_user = User.objects.create_user(
            username="panel-reader",
            email="panel-reader@example.com",
            password="test-password",
        )
        self.staff_user = User.objects.create_user(
            username="panel-staff",
            email="panel-staff@example.com",
            password="test-password",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="panel-superuser",
            email="panel-superuser@example.com",
            password="test-password",
        )
        self.target = User.objects.create_user(
            username="target-reader",
            email="target-reader@example.com",
            password="test-password",
        )

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def test_permission_matrix_for_phase_one_endpoints(self):
        cases = [
            ("get", "/api/admin-panel/stats/", None, 200),
            ("get", "/api/admin-panel/users/", None, 200),
            ("get", f"/api/admin-panel/users/{self.target.id}/", None, 200),
            ("post", f"/api/admin-panel/users/{self.target.id}/premium/", {"plan": "monthly"}, 200),
            ("delete", f"/api/admin-panel/users/{self.target.id}/premium/", None, 200),
            ("patch", f"/api/admin-panel/users/{self.target.id}/", {"is_active": True}, 200),
        ]
        for role, actor in (
            ("anonymous", None),
            ("normal", self.normal_user),
            ("staff", self.staff_user),
            ("superuser", self.superuser),
        ):
            for method, url, data, allowed_status in cases:
                with self.subTest(role=role, method=method, url=url):
                    self.client.force_authenticate(user=actor)
                    if method == "delete":
                        Subscription.objects.get_or_create(
                            user=self.target,
                            status=Subscription.STATUS_ACTIVE,
                            defaults={
                                "plan": Subscription.PLAN_MONTHLY,
                                "expires_at": timezone.now() + timedelta(days=5),
                            },
                        )
                    response = getattr(self.client, method)(url, data, format="json") if data is not None else getattr(self.client, method)(url)
                    expected = allowed_status if role in {"staff", "superuser"} else 401 if role == "anonymous" else 403
                    self.assertEqual(response.status_code, expected, response.data)

    def test_staff_cannot_change_staff_flag(self):
        self.as_user(self.staff_user)

        response = self.client.patch(
            f"/api/admin-panel/users/{self.target.id}/",
            {"is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_staff)

    def test_superuser_can_change_staff_flag(self):
        self.as_user(self.superuser)

        response = self.client.patch(
            f"/api/admin-panel/users/{self.target.id}/",
            {"is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_staff)

    def test_users_list_search_pagination_premium_filter_and_counts(self):
        author = Author.objects.create(name="Admin Panel Author")
        genre = Genre.objects.create(name="Admin Panel Genre", slug="admin-panel-genre")
        book = Book.objects.create(
            title="Panel book",
            author=author,
            genre=genre,
            owner=self.target,
        )
        from apps.reels.models import Reel

        Reel.objects.create(author=self.target, book=book, caption="Panel post")
        Subscription.objects.create(
            user=self.target,
            plan=Subscription.PLAN_MONTHLY,
            expires_at=timezone.now() + timedelta(days=30),
            provider="manual",
        )
        self.as_user(self.staff_user)

        response = self.client.get("/api/admin-panel/users/?q=target&premium=true&page=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["username"], self.target.username)
        self.assertTrue(row["is_premium"])
        self.assertEqual(row["books_count"], 1)
        self.assertEqual(row["reels_count"], 1)

        invalid_filter = self.client.get("/api/admin-panel/users/?premium=yes")
        self.assertEqual(invalid_filter.status_code, 400)

    def test_stats_counts_users_premium_content_and_recent_users(self):
        author = Author.objects.create(name="Stats Author")
        genre = Genre.objects.create(name="Stats Genre", slug="stats-genre")
        book = Book.objects.create(title="Stats book", author=author, genre=genre)
        audiobook = Audiobook.objects.create(book=book, created_by=self.target)
        Chapter.objects.create(audiobook=audiobook, title="Chapter", order=1)
        from apps.reels.models import Reel

        Reel.objects.create(author=self.target, book=book)
        Subscription.objects.create(
            user=self.target,
            plan=Subscription.PLAN_YEARLY,
            expires_at=timezone.now() + timedelta(days=100),
        )
        self.as_user(self.staff_user)

        response = self.client.get("/api/admin-panel/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], 4)
        self.assertEqual(response.data["premium_users"], 1)
        self.assertEqual(response.data["books"], 1)
        self.assertEqual(response.data["audiobooks"], 1)
        self.assertEqual(response.data["reels"], 1)
        self.assertEqual(response.data["new_users_7_days"], 4)

    def test_grant_creates_and_extends_subscription(self):
        self.as_user(self.staff_user)
        start = timezone.now()

        created = self.client.post(
            f"/api/admin-panel/users/{self.target.id}/premium/",
            {"plan": "monthly", "note": "Qo'llab-quvvatlash"},
            format="json",
        )

        self.assertEqual(created.status_code, 200)
        subscription = Subscription.objects.get(user=self.target, status=Subscription.STATUS_ACTIVE)
        self.assertEqual(subscription.provider, "manual")
        self.assertEqual(subscription.provider_ref, self.staff_user.username)
        self.assertEqual(subscription.admin_note, "Qo'llab-quvvatlash")
        self.assertGreaterEqual(subscription.expires_at, start + timedelta(days=30))
        initial_expiry = subscription.expires_at

        extended = self.client.post(
            f"/api/admin-panel/users/{self.target.id}/premium/",
            {"plan": "yearly"},
            format="json",
        )

        self.assertEqual(extended.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(Subscription.objects.filter(user=self.target, status=Subscription.STATUS_ACTIVE).count(), 1)
        self.assertEqual(subscription.expires_at, initial_expiry + timedelta(days=365))
        self.assertEqual(subscription.plan, Subscription.PLAN_YEARLY)
        self.assertEqual(
            AdminAuditLog.objects.filter(
                admin=self.staff_user,
                action="premium_granted",
                target_id=self.target.id,
            ).count(),
            2,
        )

    def test_custom_grant_requires_days_between_one_and_3650(self):
        self.as_user(self.staff_user)
        url = f"/api/admin-panel/users/{self.target.id}/premium/"

        missing_days = self.client.post(url, {"plan": "custom"}, format="json")
        too_many_days = self.client.post(url, {"plan": "custom", "days": 3651}, format="json")
        custom = self.client.post(url, {"plan": "custom", "days": 45}, format="json")

        self.assertEqual(missing_days.status_code, 400)
        self.assertEqual(too_many_days.status_code, 400)
        self.assertEqual(custom.status_code, 200)
        self.assertEqual(custom.data["plan"], Subscription.PLAN_CUSTOM)

    def test_revoke_removes_premium_access_to_chapter(self):
        book_author = Author.objects.create(name="Premium Author")
        genre = Genre.objects.create(name="Premium Genre", slug="premium-genre")
        book = Book.objects.create(title="Locked book", author=book_author, genre=genre)
        audiobook = Audiobook.objects.create(
            book=book,
            created_by=self.normal_user,
            access=Audiobook.ACCESS_PREMIUM,
        )
        chapter = Chapter.objects.create(audiobook=audiobook, title="Paid chapter", order=1)
        Subscription.objects.create(
            user=self.target,
            plan=Subscription.PLAN_MONTHLY,
            expires_at=timezone.now() + timedelta(days=10),
        )
        self.assertTrue(can_access_chapter(self.target, chapter))

        self.as_user(self.staff_user)
        response = self.client.delete(f"/api/admin-panel/users/{self.target.id}/premium/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(can_access_chapter(self.target, chapter))
        subscription = Subscription.objects.get(user=self.target)
        self.assertEqual(subscription.status, Subscription.STATUS_CANCELED)
        self.assertLessEqual(subscription.expires_at, timezone.now())
        audit = AdminAuditLog.objects.get(action="premium_revoked", target_id=self.target.id)
        self.assertEqual(audit.admin, self.staff_user)

    def test_user_detail_includes_subscription_history(self):
        subscription = Subscription.objects.create(
            user=self.target,
            plan=Subscription.PLAN_MONTHLY,
            expires_at=timezone.now() + timedelta(days=30),
            provider="manual",
            provider_ref=self.staff_user.username,
            admin_note="Admin note",
        )
        self.as_user(self.staff_user)

        response = self.client.get(f"/api/admin-panel/users/{self.target.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.target.id)
        self.assertEqual(response.data["subscriptions"][0]["id"], subscription.id)
        self.assertEqual(response.data["subscriptions"][0]["admin_note"], "Admin note")


class AdminPanelContentApiTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="content-staff",
            email="content-staff@example.com",
            password="test-password",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="content-superuser",
            email="content-superuser@example.com",
            password="test-password",
        )
        self.normal_user = User.objects.create_user(
            username="content-reader",
            email="content-reader@example.com",
            password="test-password",
        )
        self.target = User.objects.create_user(
            username="content-target",
            email="content-target@example.com",
            password="test-password",
        )
        self.author = Author.objects.create(name="Content Author")
        self.genre = Genre.objects.create(name="Content Genre", slug="content-genre")

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def create_book(self, owner=None):
        return Book.objects.create(
            title="Content book",
            author=self.author,
            genre=self.genre,
            owner=owner,
        )

    def create_reel(self, author=None, book=None, video=None):
        return Reel.objects.create(
            author=author or self.target,
            book=book,
            video=video,
            caption="Admin panel reel",
        )

    def test_content_endpoints_permission_matrix(self):
        book = self.create_book()
        audiobook = Audiobook.objects.create(book=book, created_by=self.target)
        reel = self.create_reel(book=book)
        user = self.target
        protected_requests = [
            ("get", "/api/admin-panel/books/", None, 200),
            ("get", "/api/admin-panel/reels/", None, 200),
            ("get", "/api/admin-panel/audit-log/", None, 200),
            ("get", f"/api/admin-panel/books/{book.id}/delete-preview/", None, 200),
            ("get", f"/api/admin-panel/reels/{reel.id}/delete-preview/", None, 200),
            ("patch", f"/api/admin-panel/audiobooks/{audiobook.id}/", {"access": "premium"}, 200),
        ]
        for actor, expected in (
            (None, 401),
            (self.normal_user, 403),
            (self.staff_user, 200),
            (self.superuser, 200),
        ):
            for method, url, body, success_code in protected_requests:
                self.client.force_authenticate(user=actor)
                response = (
                    getattr(self.client, method)(url, body, format="json")
                    if body is not None
                    else getattr(self.client, method)(url)
                )
                self.assertEqual(response.status_code, success_code if expected == 200 else expected)

        for actor, expected in (
            (None, 401),
            (self.normal_user, 403),
            (self.staff_user, 403),
            (self.superuser, 200),
        ):
            self.client.force_authenticate(user=actor)
            response = self.client.get(f"/api/admin-panel/users/{user.id}/delete-preview/")
            self.assertEqual(response.status_code, expected)

    def test_book_list_search_and_delete_preview_counts(self):
        book = self.create_book()
        audiobook = Audiobook.objects.create(book=book, created_by=self.target)
        chapter = Chapter.objects.create(audiobook=audiobook, title="Chapter", order=1)
        reel = self.create_reel(book=book)
        comment = Comment.objects.create(user=self.normal_user, reel=reel, text="Comment")
        Like.objects.create(user=self.normal_user, reel=reel)
        Like.objects.create(user=self.normal_user, book=book)
        Save.objects.create(user=self.normal_user, reel=reel)
        Bookmark.objects.create(
            user=self.normal_user,
            audiobook=audiobook,
            chapter=chapter,
            position=10,
        )
        Review.objects.create(user=self.normal_user, book=book, rating=4, text="Review")
        self.as_user(self.staff_user)

        listing = self.client.get("/api/admin-panel/books/?q=content")
        preview = self.client.get(f"/api/admin-panel/books/{book.id}/delete-preview/")

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["reels_count"], 1)
        counts = preview.data["will_delete"]
        self.assertEqual(counts["audiobooks"], 1)
        self.assertEqual(counts["chapters"], 1)
        self.assertEqual(counts["reels"], 1)
        self.assertEqual(counts["comments"], 1)
        self.assertEqual(counts["likes"], 2)
        self.assertEqual(counts["saves"], 1)
        self.assertEqual(counts["bookmarks"], 1)
        self.assertEqual(counts["reviews"], 1)

    def test_book_delete_removes_audiobook_and_writes_audit(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            book = self.create_book()
            book.cover.save("cover.png", SimpleUploadedFile("cover.png", b"cover"), save=True)
            audiobook = Audiobook.objects.create(
                book=book,
                created_by=self.target,
                audio_file=SimpleUploadedFile("book.mp3", b"book audio"),
            )
            chapter = Chapter.objects.create(
                audiobook=audiobook,
                title="Chapter",
                order=1,
                audio_file=SimpleUploadedFile("chapter.mp3", b"chapter audio"),
            )
            reel = self.create_reel(
                book=book,
                video=SimpleUploadedFile("reel.mp4", b"reel video"),
            )
            file_paths = [
                book.cover.path,
                audiobook.audio_file.path,
                chapter.audio_file.path,
                reel.video.path,
            ]
            self.as_user(self.staff_user)

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(f"/api/admin-panel/books/{book.id}/")

            self.assertEqual(response.status_code, 204)
            self.assertFalse(Book.objects.filter(pk=book.pk).exists())
            self.assertFalse(Audiobook.objects.filter(pk=audiobook.pk).exists())
            self.assertFalse(Chapter.objects.filter(audiobook=audiobook).exists())
            self.assertFalse(Reel.objects.filter(pk=reel.pk).exists())
            self.assertTrue(all(not os.path.exists(path) for path in file_paths))
            audit = AdminAuditLog.objects.get(action="book_deleted")
            self.assertEqual(audit.target_id, book.pk)
            self.assertEqual(audit.admin, self.staff_user)

    def test_book_and_reel_delete_permissions_for_all_roles(self):
        for actor, expected in (
            (None, 401),
            (self.normal_user, 403),
            (self.staff_user, 204),
            (self.superuser, 204),
        ):
            with self.subTest(actor=getattr(actor, "username", "anonymous")):
                book = self.create_book()
                reel = self.create_reel()
                self.client.force_authenticate(user=actor)

                book_response = self.client.delete(f"/api/admin-panel/books/{book.id}/")
                self.assertEqual(book_response.status_code, expected)
                if expected != 204:
                    self.assertTrue(Book.objects.filter(pk=book.pk).exists())
                else:
                    self.assertFalse(Book.objects.filter(pk=book.pk).exists())

                reel_response = self.client.delete(f"/api/admin-panel/reels/{reel.id}/")
                self.assertEqual(reel_response.status_code, expected)
                self.assertEqual(Reel.objects.filter(pk=reel.pk).exists(), expected != 204)

    def test_reel_delete_preview_and_delete_write_audit(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            reel = self.create_reel(video=SimpleUploadedFile("reel.mp4", b"video"))
            video_path = reel.video.path
            Comment.objects.create(user=self.normal_user, reel=reel, text="Comment")
            Like.objects.create(user=self.normal_user, reel=reel)
            self.as_user(self.staff_user)

            preview = self.client.get(f"/api/admin-panel/reels/{reel.id}/delete-preview/")
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(f"/api/admin-panel/reels/{reel.id}/")

            self.assertEqual(preview.data["will_delete"]["comments"], 1)
            self.assertEqual(preview.data["will_delete"]["likes"], 1)
            self.assertEqual(response.status_code, 204)
            self.assertFalse(Reel.objects.filter(pk=reel.pk).exists())
            self.assertFalse(os.path.exists(video_path))
            self.assertTrue(AdminAuditLog.objects.filter(action="reel_deleted", target_id=reel.pk).exists())

    def test_audiobook_access_can_be_changed_by_staff_and_invalid_value_rejected(self):
        book = self.create_book()
        audiobook = Audiobook.objects.create(book=book, created_by=self.target)
        self.as_user(self.staff_user)

        updated = self.client.patch(
            f"/api/admin-panel/audiobooks/{audiobook.id}/",
            {"access": "premium"},
            format="json",
        )
        invalid = self.client.patch(
            f"/api/admin-panel/audiobooks/{audiobook.id}/",
            {"access": "public"},
            format="json",
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(invalid.status_code, 400)
        audiobook.refresh_from_db()
        self.assertEqual(audiobook.access, Audiobook.ACCESS_PREMIUM)

    def test_ban_unban_writes_audit_entries_only_on_state_change(self):
        self.as_user(self.staff_user)
        path = f"/api/admin-panel/users/{self.target.id}/"

        banned = self.client.patch(path, {"is_active": False}, format="json")
        repeated = self.client.patch(path, {"is_active": False}, format="json")
        unbanned = self.client.patch(path, {"is_active": True}, format="json")

        self.assertEqual(banned.status_code, 200)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(unbanned.status_code, 200)
        self.assertEqual(
            list(AdminAuditLog.objects.filter(target_id=self.target.id).order_by("action").values_list("action", flat=True)),
            ["user_banned", "user_unbanned"],
        )

    def test_staff_cannot_delete_users_superuser_can_only_with_confirm(self):
        path = f"/api/admin-panel/users/{self.target.id}/"
        for actor, expected in (
            (None, 401),
            (self.normal_user, 403),
            (self.staff_user, 403),
            (self.superuser, 400),
        ):
            self.client.force_authenticate(user=actor)
            response = self.client.delete(path)
            self.assertEqual(response.status_code, expected)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

        self.as_user(self.superuser)
        missing = self.client.delete(f"/api/admin-panel/users/{self.target.id}/")
        mismatch = self.client.delete(f"/api/admin-panel/users/{self.target.id}/?confirm=wrong")
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)

    def test_superuser_cannot_delete_self_or_another_superuser(self):
        other_superuser = User.objects.create_superuser(
            username="other-superuser",
            email="other-superuser@example.com",
            password="test-password",
        )
        self.as_user(self.superuser)

        own_response = self.client.delete(
            f"/api/admin-panel/users/{self.superuser.id}/?confirm={self.superuser.username}"
        )
        other_response = self.client.delete(
            f"/api/admin-panel/users/{other_superuser.id}/?confirm={other_superuser.username}"
        )

        self.assertEqual(own_response.status_code, 400)
        self.assertEqual(other_response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())
        self.assertTrue(User.objects.filter(pk=other_superuser.pk).exists())

    def test_user_delete_removes_owned_content_and_files_after_commit(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            user = self.target
            user.avatar.save("avatar.png", SimpleUploadedFile("avatar.png", b"avatar"), save=True)
            book = self.create_book(owner=user)
            book.cover.save("cover.png", SimpleUploadedFile("cover.png", b"cover"), save=True)
            audiobook = Audiobook.objects.create(
                book=book,
                created_by=user,
                audio_file=SimpleUploadedFile("book.mp3", b"book audio"),
            )
            chapter = Chapter.objects.create(
                audiobook=audiobook,
                title="Chapter",
                order=1,
                audio_file=SimpleUploadedFile("chapter.mp3", b"chapter audio"),
            )
            reel = self.create_reel(
                author=user,
                book=book,
                video=SimpleUploadedFile("reel.mp4", b"reel video"),
            )
            Comment.objects.create(user=user, reel=reel, text="My comment")
            CommentLike.objects.create(user=user, comment=Comment.objects.first())
            Like.objects.create(user=user, reel=reel)
            Save.objects.create(user=user, reel=reel)
            file_paths = [
                user.avatar.path,
                book.cover.path,
                audiobook.audio_file.path,
                chapter.audio_file.path,
                reel.video.path,
            ]
            self.as_user(self.superuser)
            preview = self.client.get(f"/api/admin-panel/users/{user.id}/delete-preview/")
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.data["will_delete"]["books"], 1)
            self.assertEqual(preview.data["will_delete"]["reels"], 1)
            self.assertEqual(preview.data["will_delete"]["chapters"], 1)
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(
                    f"/api/admin-panel/users/{user.id}/?confirm={user.username}"
                )

            self.assertEqual(response.status_code, 204)
            self.assertFalse(User.objects.filter(pk=user.pk).exists())
            self.assertFalse(Book.objects.filter(pk=book.pk).exists())
            self.assertFalse(Audiobook.objects.filter(pk=audiobook.pk).exists())
            self.assertFalse(Reel.objects.filter(pk=reel.pk).exists())
            self.assertTrue(all(not os.path.exists(path) for path in file_paths))
            audit = AdminAuditLog.objects.get(action="user_deleted", target_id=user.pk)
            self.assertEqual(audit.details["books"], 1)
            self.assertEqual(audit.admin, self.superuser)
