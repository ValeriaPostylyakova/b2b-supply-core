from rest_framework.permissions import OR, BasePermission

from apps.accounts.permissions import IsBuyer, IsSupplier


class IsNotWarehouseRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role != "WAREHOUSE_MANAGER"


IsOrderParticipant = OR(IsBuyer, IsSupplier)
