import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.books.models import Book
from apps.borrowings.models import Borrowing

BORROWING_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id: int):
    """Return borrowing detail URL"""
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def return_url(borrowing_id: int):
    """Return borrowing return action URL"""
    return reverse(
        "borrowings:borrowing-return-borrowing", args=[borrowing_id]
    )


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required for all borrowing endpoints"""
        res_list = self.client.get(BORROWING_URL)
        res_post = self.client.post(BORROWING_URL, {})
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.client.force_authenticate(self.user)
        self.book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover="HARD",
            inventory=5,
            daily_fee=1.00,
        )

    def test_create_borrowing_success(self):
        """Test creating a borrowing is successful and inventory decreases"""
        initial_inventory = self.book.inventory
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.now().date()
            + datetime.timedelta(days=10),
        }
        res = self.client.post(BORROWING_URL, payload)
        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Borrowing.objects.count(), 1)
        borrowing = Borrowing.objects.first()
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(self.book.inventory, initial_inventory - 1)

    def test_create_borrowing_out_of_stock_fails(self):
        """Test creating borrowing for a book with 0 inventory fails"""
        self.book.inventory = 0
        self.book.save()
        payload = {
            "book": self.book.id,
            "expected_return_date": timezone.now().date()
            + datetime.timedelta(days=10),
        }
        res = self.client.post(BORROWING_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("out of stock", res.data["book"][0].lower())

    def test_list_only_own_borrowings(self):
        """Test listing only the authenticated user's borrowings"""
        other_user = get_user_model().objects.create_user(
            email="other@test.com", password="password123"
        )
        borrowing_own = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
        )
        Borrowing.objects.create(
            user=other_user,
            book=self.book,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
        )

        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], borrowing_own.id)

    def test_return_borrowing_success(self):
        """Test returning a borrowing successfully increases inventory"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
        )
        initial_inventory = self.book.inventory
        url = return_url(borrowing.id)
        res = self.client.post(url)
        borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(borrowing.actual_return_date, timezone.now().date())
        self.assertEqual(self.book.inventory, initial_inventory + 1)

    def test_return_already_returned_borrowing_fails(self):
        """Test returning an already returned borrowing raises an error"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
            actual_return_date=timezone.now().date(),
        )
        url = return_url(borrowing.id)
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been returned", res.data[0].lower())

    def test_cannot_return_other_users_borrowing(self):
        """Test that a user cannot return a borrowing belonging to another user"""
        other_user = get_user_model().objects.create_user(
            email="other@test.com", password="password123"
        )
        borrowing = Borrowing.objects.create(
            user=other_user,
            book=self.book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        url = return_url(borrowing.id)
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AdminBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="password123"
        )
        self.client.force_authenticate(self.admin)

        book1 = Book.objects.create(
            title="Book A",
            author="Author",
            cover="HARD",
            inventory=5,
            daily_fee=1.00,
        )
        book2 = Book.objects.create(
            title="Book B",
            author="Author",
            cover="SOFT",
            inventory=2,
            daily_fee=2.00,
        )

        self.borrowing_user_active = Borrowing.objects.create(
            user=self.user,
            book=book1,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
        )
        self.borrowing_admin_returned = Borrowing.objects.create(
            user=self.admin,
            book=book2,
            expected_return_date=timezone.now().date()
            + datetime.timedelta(days=5),
            actual_return_date=timezone.now().date(),
        )

    def test_list_all_borrowings_for_admin(self):
        """Test admin can see all borrowings from all users"""
        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_filter_borrowings_by_user_id(self):
        """Test admin can filter borrowings by a specific user_id"""
        res = self.client.get(BORROWING_URL, {"user_id": self.user.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(
            res.data["results"][0]["id"], self.borrowing_user_active.id
        )

    def test_filter_borrowings_is_active(self):
        """Test admin can filter borrowings by is_active status"""
        res_active = self.client.get(BORROWING_URL, {"is_active": "true"})
        res_inactive = self.client.get(BORROWING_URL, {"is_active": "false"})

        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_active.data["results"]), 1)
        self.assertEqual(
            res_active.data["results"][0]["id"], self.borrowing_user_active.id
        )

        self.assertEqual(res_inactive.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_inactive.data["results"]), 1)
        self.assertEqual(
            res_inactive.data["results"][0]["id"],
            self.borrowing_admin_returned.id,
        )
