from django.db import transaction
from django.db.models import QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from .models import Payment
from .serializers import (
    PaymentListSerializer,
    PaymentDetailSerializer,
)
from .services import get_session, is_session_paid


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset.select_related("borrowing")
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(borrowing__user=user)

        return queryset

    def get_serializer_class(self) -> type[Serializer]:
        if self.action == "retrieve":
            return PaymentDetailSerializer
        return self.serializer_class

    @action(detail=False, methods=["GET"])
    @transaction.atomic
    def success(self, request: Request) -> Response:
        """
        Handle successful Stripe payments.
        """
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"error": "session_id not found in query parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = get_session(session_id)

        try:
            payment = Payment.objects.select_for_update().get(
                session_id=session_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if is_session_paid(session):
            if payment.status != Payment.StatusChoices.PAID:
                payment.status = Payment.StatusChoices.PAID
                payment.save()
            return Response(
                {
                    "message": (
                        f"Payment successful! Borrowing ID: {payment.borrowing_id}."
                    )
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "Payment was not successful."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["GET"])
    def cancel(self, request: Request) -> Response:
        """Handle cancelled Stripe payments."""
        return Response(
            {
                "message": (
                    "Payment cancelled. You can retry later — "
                    "the session remains valid for 24 hours."
                )
            },
            status=status.HTTP_200_OK,
        )
