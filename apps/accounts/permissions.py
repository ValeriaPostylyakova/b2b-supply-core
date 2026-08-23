from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

User = get_user_model()


class IsOrganizationAdmin(BasePermission):
    message: str = "У вас нет прав для выполнения этого действия."
    ALLOWED_ROLES: set[str] = {'SUPPLIER_ADMIN', "BUYER_ADMIN"}

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user

        if not (user and user.is_authenticated and isinstance(user, User)):
            return False
        return user.role in self.ALLOWED_ROLES

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user

        if not isinstance(user, User):
            return False
        return getattr(obj, 'organization', None) == user.organization
