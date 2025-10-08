from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
)
from .serializers import BookSerializer

book_schema = extend_schema_view(
    list=extend_schema(summary="List books", responses=BookSerializer),
    retrieve=extend_schema(
        summary="Retrieve a book", responses=BookSerializer
    ),
    create=extend_schema(
        summary="Create a new book",
        request=BookSerializer,
        responses={201: BookSerializer},
    ),
    update=extend_schema(
        summary="Update a book",
        request=BookSerializer,
        responses={200: BookSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update a book",
        request=BookSerializer,
        responses={200: BookSerializer},
    ),
    destroy=extend_schema(
        summary="Delete a book",
        responses={
            204: OpenApiResponse(description="Book deleted successfully.")
        },
    ),
)
