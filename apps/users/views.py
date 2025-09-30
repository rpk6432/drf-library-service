from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    BasePermission,
)
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import UserSerializer


User = get_user_model()


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self) -> list[BasePermission]:
        """Instantiates and returns the list of permissions that this view requires."""
        if self.action == "create":
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(
        methods=["GET", "PUT", "PATCH"],
        detail=False,
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def me(self, request: Request) -> Response:
        """Retrieve or update the authenticated user's profile"""
        user = request.user
        if request.method == "GET":
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
