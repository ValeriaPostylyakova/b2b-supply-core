from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

User = get_user_model()


class IsOrganizationAdmin(BasePermission):
    message: str = "У вас нет прав для выполнения этого действия."
    ALLOWED_ROLES: set[str] = {"SUPPLIER_ADMIN", "BUYER_ADMIN"}

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user

        if not (user and user.is_authenticated and isinstance(user, User)):
            return False
        return user.role in self.ALLOWED_ROLES

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user

        if not isinstance(user, User):
            return False
        return getattr(obj, "organization", None) == user.organization


class BaseOrganizationPermission(BasePermission):
    role_name: str = None
    org_field: str = "organization"

    def has_permission(self, request: Request, view: APIView) -> bool:
        assert self.role_name is not None, "Укажите 'role_name' в вашем классе прав"
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == self.role_name
        )

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user
        obj_org = getattr(obj, self.org_field, None)
        return bool(obj_org and obj_org == getattr(user, "organization", None))


class IsSupplierAdminOwner(BaseOrganizationPermission):
    role_name = "SUPPLIER_ADMIN"
    org_field = "supplier"


class IsSupplierManagerOwner(BaseOrganizationPermission):
    role_name = "SUPPLIER_MANAGER"
    org_field = "supplier"


class IsWarehouseManagerOwner(BaseOrganizationPermission):
    role_name = "WAREHOUSE_MANAGER"
    org_field = "supplier"


class IsBuyerAdminOwner(BaseOrganizationPermission):
    role_name = "BUYER_ADMIN"
    org_field = "buyer"


class IsBuyerManagerOwner(BaseOrganizationPermission):
    role_name = "BUYER_MANAGER"
    org_field = "buyer"
