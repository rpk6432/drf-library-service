from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.borrowings.models import Borrowing
from apps.borrowings.serializers import (
    BorrowingListSerializer,
    BorrowingDetailSerializer,
)


class BorrowingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BorrowingListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Borrowing.objects.all()

        if self.action == "list":
            return queryset.select_related("book")
        if self.action == "retrieve":
            return queryset.select_related("book", "user")

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        return self.serializer_class
