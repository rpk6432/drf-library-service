from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
)
from .serializers import (
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    BorrowingCreateSerializer,
)

borrowing_schema = extend_schema_view(
    list=extend_schema(
        summary="List borrowings",
        description=(
            "Retrieve a list of borrowings.\n\n"
            "Supports filtering by user ID (for admins) and by borrowing status.\n\n"
            "### Filters\n"
            "- `user_id`: Show borrowings for a specific user (admin only)\n"
            "- `is_active`: Show active (not returned) or completed (returned) borrowings\n\n"
            "### Examples\n"
            "- Active borrowings: `GET /api/borrowings/?is_active=true`\n"
            "- Completed borrowings: `GET /api/borrowings/?is_active=false`\n"
            "- Borrowings for user 3 (admin): `GET /api/borrowings/?user_id=3`"
        ),
        responses=BorrowingListSerializer,
    ),
    retrieve=extend_schema(
        summary="Retrieve a borrowing",
        responses=BorrowingDetailSerializer,
    ),
    create=extend_schema(
        summary="Create a borrowing",
        request=BorrowingCreateSerializer,
        responses={201: BorrowingDetailSerializer},
    ),
    return_borrowing=extend_schema(
        summary="Return a borrowed book",
        description=(
            "Mark the borrowing as returned and increase the book inventory. "
            "If returned late, a fine payment session will be generated."
        ),
        responses={
            200: BorrowingDetailSerializer,
            400: OpenApiResponse(
                description="This borrowing has already been returned."
            ),
            403: OpenApiResponse(
                description="You cannot return this borrowing."
            ),
        },
    ),
)
