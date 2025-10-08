from rest_framework import viewsets

from .models import Book
from .permissions import IsAdminUserOrReadOnly
from .schemas import book_schema
from .serializers import BookSerializer


@book_schema
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminUserOrReadOnly,)
