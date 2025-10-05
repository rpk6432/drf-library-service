from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Payment
from .serializers import (
    PaymentListSerializer,
    PaymentDetailSerializer,
)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset.select_related("borrowing")
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(borrowing__user=user)

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return self.serializer_class

    @action(
        methods=["GET"],
        detail=False,
        url_path="success",
    )
    def success(self, request):
        """Endpoint for successful Stripe payments."""
        return Response({"message": "Payment successful!"})

    @action(
        methods=["GET"],
        detail=False,
        url_path="cancel",
    )
    def cancel(self, request):
        """Endpoint for cancelled Stripe payments."""
        return Response({"message": "Payment can be made later."})
