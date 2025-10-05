import datetime
from decimal import Decimal

import stripe
from django.urls import reverse
from rest_framework.request import Request

from apps.books.models import Book


def prepare_stripe_session(
    book: Book,
    request: Request,
    expected_return_date: datetime.date,
    borrow_date: datetime.date,
) -> tuple[stripe.checkout.Session, Decimal]:
    """
    Create a Stripe Checkout session and return it with the total rental cost
    """
    days_rented = (expected_return_date - borrow_date).days
    money_to_pay = round(book.daily_fee * days_rented, 2)

    success_url = (
        request.build_absolute_uri(reverse("payments:payment-success"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("payments:payment-cancel"))

    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": book.title},
                    "unit_amount": int(money_to_pay * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session, money_to_pay
