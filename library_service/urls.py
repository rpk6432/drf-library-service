from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/books/", include("apps.books.urls", namespace="books")),
    path(
        "api/borrowings/",
        include("apps.borrowings.urls", namespace="borrowings"),
    ),
]
