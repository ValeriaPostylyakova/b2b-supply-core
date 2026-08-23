from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.permissions import IsOrganizationAdmin
from apps.accounts.serializers import (
    CustomTokenObtainPairSerializer,
    UserDetailSerializer,
    UsersViewSetCreateSerializer,
    UsersViewSetSerializer,
)
from config import settings

User = get_user_model()

class CookieTokenObtainView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh_token = response.data.pop('refresh')

            response.set_cookie(
                key=settings.SIMPLE_JWT['AUTH_COOKIE'],
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=3600 * 24
            )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        cookie_name = settings.SIMPLE_JWT['AUTH_COOKIE']
        refresh_token = request.COOKIES.get(cookie_name)

        if refresh_token:
            request.data['refresh'] = refresh_token
        return super().post(request, *args, **kwargs)

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = User.objects.select_related('organization').get(id=request.user.id)
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UsersViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    lookup_field = 'external_id'

    def get_queryset(self):
        return User.objects.filter(organization=self.request.user.organization)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UsersViewSetCreateSerializer
        return UsersViewSetSerializer

    def perform_destroy(self, instance: User) -> None:
        instance.is_active = False
        instance.save()




