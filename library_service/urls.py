from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/books/", include("apps.books.urls", namespace="books")),
    path(
        "api/borrowings/",
        include("apps.borrowings.urls", namespace="borrowings"),
    ),
    path("api/payments/", include("apps.payments.urls", namespace="payments")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
