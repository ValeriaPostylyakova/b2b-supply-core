from rest_framework import permissions


class IsSupplierAdminVerifyOrganization(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.role == "SUPPLIER_ADMIN"
            and request.user.organization.verification_status == "VERIFIED"
        )
