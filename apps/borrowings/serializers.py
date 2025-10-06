from datetime import datetime

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.books.serializers import BookSerializer
from .models import Borrowing
from ..books.models import Book
from ..payments.serializers import PaymentListSerializer


class BorrowingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "book_title",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        )


class BorrowingListAdminSerializer(BorrowingListSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        source="user.id", read_only=True
    )

    class Meta(BorrowingListSerializer.Meta):
        fields = BorrowingListSerializer.Meta.fields + ("user_id",)


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    payments = PaymentListSerializer(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "user_id",
            "user_email",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "payments",
        )


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("book", "expected_return_date")

    def validate_book(self, value: Book) -> Book:
        if value.inventory == 0:
            raise ValidationError("This book is out of stock.")
        return value

    def validate_expected_return_date(self, value: datetime) -> datetime:
        if value <= timezone.now().date():
            raise ValidationError(
                "Expected return date must be in the future."
            )
        return value
