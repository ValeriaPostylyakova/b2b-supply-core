from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsBuyerAdminOwner,
    IsBuyerManagerOwner,
    IsSupplierAdminOwner,
    IsSupplierManagerOwner,
)
from apps.orders.models import Order


class OrdersViewSet(ModelViewSet):
    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        permission_classes = super().get_permissions()
        if self.action == "list":
            permission_classes.append(
                IsSupplierManagerOwner()
                | IsBuyerManagerOwner()
                | IsSupplierAdminOwner()
                | IsBuyerAdminOwner()
            )
        return permission_classes
