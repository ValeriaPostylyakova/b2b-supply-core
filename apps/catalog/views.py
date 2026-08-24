from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import permissions, generics, status
from rest_framework.response import Response

from apps.catalog.models import Product, Stock
from apps.catalog.paginations import ProductNumberPagination
from apps.catalog.permissions import IsSupplierAdminOwner, IsSupplerManagerOwner
from apps.catalog.serializers import (
    ProductFilter,
    ProductListSerializer,
    ProductListDetailSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
)

User = get_user_model()


from django.db.models import Sum, Value, F, Prefetch
from django.db.models.functions import Coalesce

class ProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = ProductFilter
    pagination_class = ProductNumberPagination

    def get_queryset(self):
        queryset = self.queryset.all()

        user = self.request.user
        user_role = getattr(user, "role", "")
        is_supplier_user_role = isinstance(user_role, str) and user_role.startswith(
            "SUPPLIER_"
        )

        if is_supplier_user_role:
            if hasattr(user, "organization") and user.organization:
                queryset = queryset.filter(supplier=user.organization)

            supplier_stock_filter = models.Q(
                stocks__warehouse__supplier=user.organization
            )

            total_quantity = Coalesce(
                Sum("stocks__quantity", filter=supplier_stock_filter), Value(0)
            )
            total_reserved = Coalesce(
                Sum("stocks__reserved_quantity", filter=supplier_stock_filter), Value(0)
            )

            queryset = queryset.annotate(
                available_quantity=total_quantity - total_reserved,
                quantity=total_quantity,
                reserved_quantity=total_reserved,
            )
        else:
            all_total_quantity = Coalesce(Sum("stocks__quantity"), Value(0))
            all_total_reserved = Coalesce(Sum("stocks__reserved_quantity"), Value(0))
            queryset = queryset.annotate(
                available_quantity=all_total_quantity - all_total_reserved,
            )

        return queryset


class ProductRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductListDetailSerializer

    lookup_field = 'external_id'

    def get_queryset(self):
        queryset = self.queryset.all()
        user = self.request.user
        user_role = getattr(user, "role", "")
        is_supplier_user_role = isinstance(user_role, str) and user_role.startswith(
            "SUPPLIER_"
        )

        if is_supplier_user_role and hasattr(user, "organization") and user.organization:
            queryset = queryset.filter(supplier=user.organization)
            queryset = queryset.prefetch_related(
                Prefetch("stocks",
                    queryset=Stock.objects.filter(
                    warehouse__supplier=user.organization
                ).select_related('warehouse'))
            )
        else:
            queryset = queryset.prefetch_related(
                Prefetch("stocks", queryset=Stock.objects.all().select_related('warehouse'))
            )

        return queryset

class ProductCreateAPIView(generics.CreateAPIView):
    queryset = Product.objects.all().select_related('supplier')
    serializer_class = ProductCreateSerializer
    permission_classes = [permissions.IsAuthenticated & (IsSupplierAdminOwner | IsSupplerManagerOwner)]

class ProductUpdateAPIView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductUpdateSerializer
    permission_classes = [permissions.IsAuthenticated & (IsSupplierAdminOwner | IsSupplerManagerOwner)]
    lookup_field = 'external_id'

class ProductDestroyAPIView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    permission_classes = [
        permissions.IsAuthenticated & (IsSupplierAdminOwner | IsSupplerManagerOwner)
    ]
    lookup_field = "external_id"

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.is_active:
            return Response(
                {"detail": "Товар уже деактивирован."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.is_active = False
        instance.save()

        return Response(
            {"detail": "Товар успешно деактивирован."},
            status=status.HTTP_200_OK
        )