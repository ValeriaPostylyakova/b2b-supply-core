from rest_framework.permissions import BasePermission


class IsNotWarehouseRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role != "WAREHOUSE_MANAGER"
