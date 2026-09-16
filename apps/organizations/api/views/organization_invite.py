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
)
from apps.organizations.models.organization_invite import OrganizationInvite
from apps.organizations.services.organization_invite import (
    OrganizationInviteService,
)


class InviteAcceptAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InviteAcceptRateThrottle]

    def post(self, request):
        serializer = OrganizationAcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user, is_new_user = OrganizationInviteService.accept_invite(token)

        return Response(
            {
                "is_new_user": is_new_user,
                "email": user.email,
                "organization_name": user.organization.name,
            },
            status=status.HTTP_200_OK,
        )


class InviteRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OrganizationAcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user, is_new_user = OrganizationInviteService.accept_invite(token)

        return Response(
            {
                "is_new_user": is_new_user,
                "email": user.email,
                "organization_name": user.organization.name,
            },
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

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationInviteCreateSerializer
        return OrganizationInviteListSerializer

    def get_queryset(self):
        return self.queryset.filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]
        org = self.request.user.organization
        OrganizationInviteService.create_invite(email, org, role)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": "Приглашение успешно принято в обработку"},
            status=status.HTTP_201_CREATED,
        )
