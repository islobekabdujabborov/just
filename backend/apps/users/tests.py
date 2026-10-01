from rest_framework.test import APITestCase

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

    def test_authenticated_user_can_follow_and_unfollow(self):
        self.client.force_authenticate(self.viewer)
        path = "/api/users/creator/follow/"

        followed = self.client.post(path, {}, format="json")
        self.assertEqual(followed.status_code, 200)
        self.assertTrue(followed.data["is_following"])
        self.assertTrue(Follow.objects.filter(follower=self.viewer, followed=self.creator).exists())

        profile = self.client.get("/api/users/creator/")
        self.assertTrue(profile.data["is_following"])

        unfollowed = self.client.delete(path)
        self.assertEqual(unfollowed.status_code, 200)
        self.assertFalse(unfollowed.data["is_following"])
        self.assertFalse(Follow.objects.filter(follower=self.viewer, followed=self.creator).exists())