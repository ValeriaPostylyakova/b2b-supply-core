from django.core import signing
from rest_framework import mixins, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.common.throttles import InviteAcceptRateThrottle
from apps.organizations.api.permissions import (
    IsOrganizationAdmin,
)
from apps.organizations.api.serializers.organization_invite import (
    OrganizationAcceptInviteSerializer,
    OrganizationInviteCreateSerializer,
    OrganizationInviteListSerializer,
    OrganizationInviteRegistrationSerializer,
)
from apps.organizations.models.organization_invite import OrganizationInvite
from apps.organizations.services.organization_invite import (
    OrganizationInviteService,
)

REGISTRATION_SALT = "user-complete-registration-salt"


class InviteAcceptAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InviteAcceptRateThrottle]

    def post(self, request):
        serializer = OrganizationAcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        user, is_new_user = OrganizationInviteService.accept_invite(token)

        response_data = {
            "is_new_user": is_new_user,
            "email": user.email,
            "organization_name": user.organization.name,
            "registration_token": None,
        }

        if is_new_user:
            response_data["registration_token"] = signing.dumps(
                {"user_id": user.id}, salt=REGISTRATION_SALT
            )

        return Response(response_data, status=status.HTTP_200_OK)


class InviteRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OrganizationInviteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        reg_token = validated_data.pop("registration_token")

        OrganizationInviteService.register_invited_user(
            registration_token=reg_token, reg_salt=REGISTRATION_SALT, **validated_data
        )

        return Response(
            {"message": "Профиль успешно настроен. Теперь вы можете войти."},
            status=status.HTTP_200_OK,
        )


class OrganizationInviteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = OrganizationInvite.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    lookup_field = "external_id"

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationInviteCreateSerializer
        return OrganizationInviteListSerializer

    def get_queryset(self):
        return self.queryset.filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        org = self.request.user.organization
        OrganizationInviteService.create_invite(serializer.validated_data, org)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        response = Response(
            {"detail": "Приглашение успешно принято в обработку"},
            status=status.HTTP_201_CREATED,
        )
        return response
