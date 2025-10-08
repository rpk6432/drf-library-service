from typing import Type

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from apps.borrowings.models import Borrowing
from apps.borrowings.schemas import borrowing_schema
from apps.borrowings.serializers import (
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    BorrowingCreateSerializer,
    BorrowingListAdminSerializer,
)
from apps.payments.models import Payment
from apps.payments.services import create_payment_session, create_fine_session
from library_service.telegram.services import send_telegram_message


@borrowing_schema
class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BorrowingListSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Borrowing.objects.all()

    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def return_borrowing(
        self, request: Request, pk: int | None = None
    ) -> Response:
        borrowing = self.get_object()
        book = borrowing.book

        if borrowing.actual_return_date:
            raise ValidationError("This borrowing has already been returned.")

        if not request.user.is_staff and borrowing.user != request.user:
            raise PermissionDenied("You cannot return this borrowing.")

        borrowing.actual_return_date = timezone.now().date()
        borrowing.save()

        book.inventory += 1
        book.save()

        if borrowing.actual_return_date > borrowing.expected_return_date:
            try:
                stripe_session, fine_amount = create_fine_session(
                    borrowing, request
                )
            except Exception as e:
                raise ValidationError(
                    f"Error preparing fine payment session: {e}"
                )

            Payment.objects.create(
                status="PENDING",
                type=Payment.TypeChoices.FINE,
                borrowing=borrowing,
                session_url=stripe_session.url,
                session_id=stripe_session.id,
                money_to_pay=fine_amount,
            )

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset
        user = self.request.user

        # If the user is not a staff member, limit queryset to their own borrowings.
        # If the user is staff and provides a "user_id" query parameter,
        # filter the queryset to show only borrowings of that specific user.
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        if user.is_staff and (
            user_id := self.request.query_params.get("user_id")
        ):
            queryset = queryset.filter(user_id=user_id)

        # Filter borrowings by "is_active" param:
        # active (not returned) or completed (returned).
        is_active_param = self.request.query_params.get("is_active")

        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1", "yes")

            if is_active:
                queryset = queryset.filter(actual_return_date__isnull=True)
            else:
                queryset = queryset.filter(actual_return_date__isnull=False)

        if self.action == "list":
            return queryset.select_related("book")
        if self.action == "retrieve":
            return queryset.select_related("book", "user").prefetch_related(
                "payments"
            )

        return queryset

    def get_serializer_class(self) -> Type[Serializer]:
        user = self.request.user

        if self.action == "list" and user.is_staff:
            return BorrowingListAdminSerializer

        if self.action == "retrieve":
            return BorrowingDetailSerializer

        if self.action == "create":
            return BorrowingCreateSerializer

        return self.serializer_class

    def perform_create(self, serializer: BorrowingCreateSerializer) -> None:
        validated_data = serializer.validated_data
        book = validated_data["book"]
        expected_return_date = validated_data["expected_return_date"]
        borrow_date = timezone.now().date()

        try:
            stripe_session, money_to_pay = create_payment_session(
                book, self.request, expected_return_date, borrow_date
            )
        except Exception as e:
            raise ValidationError(f"Error preparing Stripe session: {e}")

        with transaction.atomic():
            book.inventory -= 1
            book.save()

            borrowing = serializer.save(user=self.request.user)

            Payment.objects.create(
                status="PENDING",
                type="PAYMENT",
                borrowing=borrowing,
                session_url=stripe_session.url,
                session_id=stripe_session.id,
                money_to_pay=money_to_pay,
            )

            transaction.on_commit(
                lambda: send_telegram_message(
                    f"New borrowing created\n\n"
                    f"Book: *{borrowing.book.title}*\n"
                    f"User: `{borrowing.user.email}`\n"
                    f"Expected return date: {borrowing.expected_return_date}"
                )
            )

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Use detail serializer to return full borrowing info in the response.
        detail_serializer = BorrowingDetailSerializer(serializer.instance)

        headers = self.get_success_headers(detail_serializer.data)
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )
