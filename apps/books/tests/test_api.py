from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.books.models import Book
from apps.books.serializers import BookSerializer

BOOK_URL = reverse("books:book-list")


def detail_url(book_id: int):
    return reverse("books:book-detail", args=[book_id])


class UnauthenticatedBookApiTests(TestCase):
    """Test the publicly available book API features"""

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.book1 = Book.objects.create(
            title="Test Book 1",
            author="Test Author 1",
            cover="HARD",
            inventory=5,
            daily_fee=0.99,
        )
        cls.book2 = Book.objects.create(
            title="Another Book",
            author="Another Author",
            cover="SOFT",
            inventory=1,
            daily_fee=1.49,
        )

    def test_list_books_succeeds(self):
        """Test retrieving a list of books is successful"""
        res = self.client.get(BOOK_URL)
        books = Book.objects.order_by("title")
        serializer = BookSerializer(books, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_book_detail_succeeds(self):
        """Test retrieving book detail is successful"""
        url = detail_url(self.book1.id)
        res = self.client.get(url)
        serializer = BookSerializer(self.book1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_book_unauthenticated_fails(self):
        """Test creating a book without authentication fails"""
        payload = {
            "title": "New Book",
            "author": "New Author",
            "cover": "SOFT",
            "inventory": 1,
            "daily_fee": 1.50,
        }
        res = self.client.post(BOOK_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBookApiTests(TestCase):
    """Test book API features for a regular authenticated user"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.client.force_authenticate(self.user)
        self.book = Book.objects.create(
            title="Test Book 2",
            author="Test Author 2",
            cover="SOFT",
            inventory=3,
            daily_fee=2.99,
        )

    def test_create_book_forbidden(self):
        """Test that a regular user cannot create a book"""
        payload = {
            "title": "Forbidden Book",
            "author": "Regular User",
            "cover": "SOFT",
            "inventory": 1,
            "daily_fee": 1.00,
        }
        res = self.client.post(BOOK_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_book_forbidden(self):
        """Test that a regular user cannot delete a book"""
        url = detail_url(self.book.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    """Test book API features for an admin user"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@test.com", password="password123"
        )
        self.client.force_authenticate(self.admin_user)
        self.book = Book.objects.create(
            title="Admin Book",
            author="Admin Author",
            cover="HARD",
            inventory=10,
            daily_fee=5.00,
        )

    def test_create_book_succeeds(self):
        """Test that an admin can create a book"""
        payload = {
            "title": "New Book by Admin",
            "author": "Admin Author",
            "cover": "HARD",
            "inventory": 2,
            "daily_fee": 3.25,
        }
        res = self.client.post(BOOK_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        book = Book.objects.get(id=res.data["id"])
        for key, value in payload.items():
            if key == "daily_fee":
                self.assertEqual(getattr(book, key), Decimal(str(value)))
            else:
                self.assertEqual(getattr(book, key), value)

    def test_create_book_with_invalid_data_fails(self):
        """Test creating a book with missing title fails"""
        payload = {
            "author": "Author Without Title",
            "cover": "SOFT",
            "inventory": 1,
            "daily_fee": 1.99,
        }
        res = self.client.post(BOOK_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)

    def test_partial_update_book_succeeds(self):
        """Test that an admin can partially update a book"""
        payload = {"title": "Updated Title", "daily_fee": 9.99}
        url = detail_url(self.book.id)
        res = self.client.patch(url, payload)
        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.book.title, payload["title"])
        self.assertEqual(
            self.book.daily_fee, Decimal(str(payload["daily_fee"]))
        )
        self.assertEqual(self.book.author, "Admin Author")

    def test_delete_book_succeeds(self):
        """Test that an admin can delete a book"""
        url = detail_url(self.book.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(id=self.book.id).exists())
