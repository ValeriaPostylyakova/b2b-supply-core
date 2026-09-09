from rest_framework import permissions
from rest_framework.generics import RetrieveUpdateAPIView

from apps.organizations.api.permissions import (
    IsActiveUserOrganization,
    IsOrganizationAdmin,
)
from apps.organizations.api.serializers import OrganizationBaseSerializer
from apps.organizations.models import Organization


class MyCompanyAPIView(RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsActiveUserOrganization]
    serializer_class = OrganizationBaseSerializer

    def get_object(self):
        return self.request.user.organization

    def get_permissions(self):
        if self.request.method == "PATCH":
            self.permission_classes.append(IsOrganizationAdmin)

        return super().get_permissions()

    def perform_update(self, serializer):
        serializer.instance.verification_status = "PENDING"
        serializer.save()
