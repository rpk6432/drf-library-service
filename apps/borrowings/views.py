from typing import Type

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
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
