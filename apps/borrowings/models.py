from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, F

from apps.books.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="borrowings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )

    class Meta:
        ordering = ["-borrow_date"]
        verbose_name = "Borrowing"
        verbose_name_plural = "Borrowings"
        constraints = [
            CheckConstraint(
                check=Q(expected_return_date__gt=F("borrow_date")),
                name="expected_return_date_gt_borrow_date",
            ),
            CheckConstraint(
                check=Q(actual_return_date__isnull=True)
                | Q(actual_return_date__gte=F("borrow_date")),
                name="actual_return_date_gte_borrow_date_if_not_null",
            ),
        ]

    def __str__(self):
        return f"Borrowed {self.book.title} by {self.user.email}"
