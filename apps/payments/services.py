import datetime
from decimal import Decimal
import stripe
from django.conf import settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from stripe.billing_portal import Session

from apps.books.models import Book
from apps.borrowings.models import Borrowing


def _create_stripe_session(
    request: Request,
    product_name: str,
    money_to_pay: Decimal,
) -> stripe.checkout.Session:
    success_url = (
        request.build_absolute_uri(reverse("payments:payment-success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("payments:payment-cancel"))

    return stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": product_name},
                    "unit_amount": int(money_to_pay * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )


def create_payment_session(
    book: Book,
    request: Request,
    expected_return_date: datetime.date,
    borrow_date: datetime.date,
) -> tuple[stripe.checkout.Session, Decimal]:
    """
    Create a Stripe session for a regular borrowing payment.
    """
    days_rented = (expected_return_date - borrow_date).days
    money_to_pay = round(book.daily_fee * days_rented, 2)
    product_name = book.title

    session = _create_stripe_session(request, product_name, money_to_pay)

    return session, money_to_pay


def create_fine_session(
    borrowing: Borrowing,
    request: Request,
) -> tuple[stripe.checkout.Session, Decimal]:
    """
    Create a Stripe session for an overdue fine payment.
    """
    days_overdue = (
        borrowing.actual_return_date - borrowing.expected_return_date
    ).days
    fine_amount = round(
        borrowing.book.daily_fee * days_overdue * settings.FINE_MULTIPLIER, 2
    )
    product_name = f"Fine for overdue: {borrowing.book.title}"

    session = _create_stripe_session(request, product_name, fine_amount)

    return session, fine_amount


def get_session(session_id: str) -> Session:
    """Retrieve a Stripe Checkout session."""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except stripe.error.InvalidRequestError as e:
        raise ValidationError(f"Invalid Stripe session ID: {e}")
    except Exception as e:
        raise ValidationError(f"Stripe error: {e}")


def is_session_paid(session: Session) -> bool:
    """Return True if the session is fully paid."""
    return session.payment_status == "paid"
