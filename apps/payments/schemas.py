from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
)
from .serializers import PaymentListSerializer, PaymentDetailSerializer

payment_schema = extend_schema_view(
    list=extend_schema(
        summary="List payments", responses=PaymentListSerializer
    ),
    retrieve=extend_schema(
        summary="Retrieve a payment", responses=PaymentDetailSerializer
    ),
    success=extend_schema(
        summary="Handle successful payment",
        responses={
            200: OpenApiResponse(description="Payment marked as PAID."),
            400: OpenApiResponse(
                description="Missing session_id or payment not successful."
            ),
            404: OpenApiResponse(description="Payment record not found."),
        },
    ),
    cancel=extend_schema(
        summary="Handle cancelled payment",
        responses={
            200: OpenApiResponse(description="Payment cancelled successfully.")
        },
    ),
)
