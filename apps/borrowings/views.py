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

        if self.action == "list":
            return queryset.select_related("book")
        if self.action == "retrieve":
            return queryset.select_related("book", "user")

        return queryset

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "retrieve":
            return BorrowingDetailSerializer
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
