from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.serializers import UserSerializer

CREATE_USER_URL = reverse("users:user-list")
TOKEN_URL = reverse("users:token_obtain_pair")
ME_URL = reverse("users:user-me")

User = get_user_model()


class PublicUserApiTests(TestCase):
    """Test the publicly available API features"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a new user is successful"""
        payload = {
            "email": "new_user@example.com",
            "password": "new_password123",
            "first_name": "Test",
            "last_name": "User",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_create_user_with_existing_email_fails(self):
        """Test error is returned if registering with an existing email"""
        User.objects.create_user(
            email="test@example.com", password="password123"
        )
        payload = {
            "email": "test@example.com",
            "password": "password123",
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_success(self):
        """Test creating a JWT token is successful"""
        user = User.objects.create_user(
            email="test@example.com", password="password123"
        )
        payload = {
            "email": user.email,
            "password": "password123",
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_create_token_with_bad_credentials_fails(self):
        """Test getting a token with bad credentials fails"""
        User.objects.create_user(
            email="test@example.com", password="password123"
        )
        payload = {"email": "test@example.com", "password": "wrongpassword"}
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_profile_unauthenticated_fails(self):
        """Test that retrieving a profile unauthenticated fails"""
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test the API features available for authenticated users"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="private@example.com",
            password="password123",
        )
        res = self.client.post(
            TOKEN_URL, {"email": self.user.email, "password": "password123"}
        )
        self.client.credentials(HTTP_AUTHORIZE=f"{res.data['access']}")

    def test_retrieve_profile_authenticated_success(self):
        """Test retrieving profile for an authenticated user"""
        res = self.client.get(ME_URL)
        serializer = UserSerializer(self.user)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.keys(), serializer.data.keys())
        self.assertEqual(res.data["email"], serializer.data["email"])

    def test_update_profile_authenticated_success(self):
        """Test updating the profile for an authenticated user"""
        payload = {"first_name": "NewFirstName", "last_name": "NewLastName"}
        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.first_name, payload["first_name"])
        self.assertEqual(self.user.last_name, payload["last_name"])

    def test_update_password_authenticated_success(self):
        """Test updating password for an authenticated user"""
        payload = {"password": "newpassword123"}
        res = self.client.patch(ME_URL, payload)
        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
