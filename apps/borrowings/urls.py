from rest_framework import routers

from .views import BorrowingViewSet

router = routers.DefaultRouter()
router.register("", BorrowingViewSet, basename="borrowing")

urlpatterns = router.urls

app_name = "borrowings"
