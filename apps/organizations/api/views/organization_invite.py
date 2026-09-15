from rest_framework import mixins, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

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

PERMISSION_CLASSES = [permissions.IsAuthenticated, IsOrganizationAdmin]


class InviteCreateAPIView(APIView):
    permission_classes = PERMISSION_CLASSES

    def post(self, request):
        serializer = OrganizationInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]
        org = request.user.organization

        OrganizationInviteService.create_invite(email, role, org)

        return Response(
            {"detail": "Приглашение успешно отправлено"}, status=status.HTTP_201_CREATED
        )


class InviteAcceptAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OrganizationAcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        user = OrganizationInviteService.accept_invite(token)

        is_new_user = not user.has_usable_password()

        return Response(
            {
                "is_new_user": is_new_user,
                "email": user.email,
                "organization_name": user.organization.name,
            },
            status=status.HTTP_200_OK,
        )


class MyCompanyInviteViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = OrganizationInvite.objects.all()
    serializer_class = OrganizationInviteListSerializer
    permission_classes = PERMISSION_CLASSES

    def get_queryset(self):
        user_org = self.request.user.organization
        queryset = self.queryset.filter(organization=user_org)
        return queryset
