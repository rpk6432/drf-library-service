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
from apps.borrowings.serializers import (
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    BorrowingCreateSerializer,
    BorrowingListAdminSerializer,
)


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

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        if user.is_staff and (
            user_id := self.request.query_params.get("user_id")
        ):
            queryset = queryset.filter(user_id=user_id)

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
            return queryset.select_related("book", "user")

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

    @transaction.atomic
    def perform_create(self, serializer: Serializer) -> None:
        """
        Attach the current user to the borrowing and decrease book inventory.
        """
        book = serializer.validated_data["book"]
        book.inventory -= 1
        book.save()

        serializer.save(user=self.request.user)
