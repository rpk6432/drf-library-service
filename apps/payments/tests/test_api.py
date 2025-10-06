import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.books.models import Book
from apps.borrowings.models import Borrowing
from apps.payments.models import Payment
from apps.payments.serializers import PaymentDetailSerializer

PAYMENT_URL = reverse("payments:payment-list")


def detail_url(payment_id: int):
    return reverse("payments:payment-detail", args=[payment_id])


class UnauthenticatedPaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access payment endpoints"""
        res = self.client.get(PAYMENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.client.force_authenticate(self.user)

        book = Book.objects.create(
            title="Test Book",
            author="Author",
            cover="HARD",
            inventory=1,
            daily_fee=1.00,
        )
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        self.payment = Payment.objects.create(
            status="PENDING",
            type="PAYMENT",
            borrowing=borrowing,
            session_url="http://example.com",
            session_id="test_session_id_123",
            money_to_pay=10.00,
        )

    def test_list_only_own_payments(self):
        """Test that a regular user can only see their own payments"""
        other_user = get_user_model().objects.create_user(
            email="other@test.com", password="password123"
        )
        other_borrowing = Borrowing.objects.create(
            user=other_user,
            book=self.payment.borrowing.book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        Payment.objects.create(
            status="PENDING",
            type="PAYMENT",
            borrowing=other_borrowing,
            session_url="http://example.com/other",
            session_id="test_session_id_456",
            money_to_pay=5.00,
        )

        res = self.client.get(PAYMENT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], self.payment.id)

    def test_retrieve_own_payment_detail(self):
        """Test retrieving detail for own payment is successful"""
        url = detail_url(self.payment.id)
        res = self.client.get(url)
        serializer = PaymentDetailSerializer(self.payment)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_cannot_retrieve_other_users_payment_detail(self):
        """Test that retrieving detail for another user's payment fails"""
        other_user = get_user_model().objects.create_user(
            email="other@test.com", password="password123"
        )
        other_borrowing = Borrowing.objects.create(
            user=other_user,
            book=self.payment.borrowing.book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        other_payment = Payment.objects.create(
            borrowing=other_borrowing,
            session_url="http://example.com/other",
            session_id="test_session_id_456",
            money_to_pay=5.00,
        )

        url = detail_url(other_payment.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AdminPaymentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="password123"
        )
        self.client.force_authenticate(self.admin)

        book = Book.objects.create(
            title="Admin Book",
            author="Author",
            cover="SOFT",
            inventory=1,
            daily_fee=1.00,
        )
        borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        borrowing2 = Borrowing.objects.create(
            user=self.admin,
            book=book,
            expected_return_date=(
                timezone.now().date() + datetime.timedelta(days=1)
            ),
        )
        self.payment1 = Payment.objects.create(
            borrowing=borrowing1,
            session_url="http://e.com/1",
            session_id="1",
            money_to_pay=1,
        )
        self.payment2 = Payment.objects.create(
            borrowing=borrowing2,
            session_url="http://e.com/2",
            session_id="2",
            money_to_pay=2,
        )

    def test_list_all_payments_as_admin(self):
        """Test that an admin can list all payments from all users"""
        res = self.client.get(PAYMENT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
