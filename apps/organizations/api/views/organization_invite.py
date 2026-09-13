from rest_framework import mixins, permissions
from rest_framework.viewsets import GenericViewSet

from apps.organizations.api.permissions import (
    IsOrganizationAdmin,
)
from apps.organizations.api.serializers.organization_invite import (
    OrganizationInviteCreateSerializer,
    OrganizationInviteSerializer,
)
from apps.organizations.models.organization_invite import OrganizationInvite


class MyCompanyEmployeesViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = OrganizationInvite.objects.all()
    serializer_class = OrganizationInviteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]

    def get_queryset(self):
        user_org = self.request.user.organization
        queryset = self.queryset.filter(organization=user_org)
        return queryset

    def get_serializer(self, *args, **kwargs):
        if self.method == "POST":
            return OrganizationInviteCreateSerializer
        return super().get_serializer(*args, **kwargs)
