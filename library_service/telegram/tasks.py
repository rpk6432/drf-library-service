from django.utils import timezone

from apps.borrowings.models import Borrowing
from .services import send_telegram_message


def check_overdue_borrowings() -> None:
    """Check for overdue borrowings and notify via Telegram."""
    today = timezone.now().date()

    overdue_borrowings = Borrowing.objects.filter(
        expected_return_date__lte=today, actual_return_date__isnull=True
    ).select_related("user", "book")

    if not overdue_borrowings.exists():
        send_telegram_message("No borrowings overdue today!")
        return

    for borrowing in overdue_borrowings:
        days_overdue = (today - borrowing.expected_return_date).days
        message = (
            f"OVERDUE BORROWING\n\n"
            f"User: `{borrowing.user.email}`\n"
            f"Book: *{borrowing.book.title}*\n"
            f"Overdue by: *{days_overdue} day(s)*"
        )
        send_telegram_message(message)
