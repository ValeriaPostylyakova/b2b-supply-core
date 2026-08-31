from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, F, Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import UpdateModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import (
    IsSupplierAdminOwner,
    IsSupplierAdminRole,
    IsSupplierManagerOwner,
    IsWarehouseManagerOwner,
)
from apps.catalog.models import PriceListImport, Product, Stock, Warehouse
from apps.catalog.paginations import ProductNumberPagination, StockNumberPagination
from apps.catalog.serializers import (
    ProductCreateSerializer,
    ProductFilter,
    ProductListDetailSerializer,
    ProductListSerializer,
    ProductUpdateSerializer,
    StockListSerializer,
    StockReportsSerializer,
    StockUpdateSerializer,
    WarehouseCreateUpdateSerializer,
    WarehouseFilter,
    WarehouseListSerializer,
)

User = get_user_model()


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    lookup_field = "external_id"
    filterset_class = ProductFilter
    pagination_class = ProductNumberPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "retrieve":
            return ProductListDetailSerializer
        if self.action == "create":
            return ProductCreateSerializer
        if self.action in ["partial_update"]:
            return ProductUpdateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [
                permissions.IsAuthenticated()
                & (IsSupplierAdminOwner() | IsSupplierManagerOwner())
            ]
        return super().get_permissions()

    def get_queryset(self):
        queryset = self.queryset.all()
        user = self.request.user

        if self.action == "create":
            return queryset.select_related("supplier")

        if self.action == "list":
            if user.is_supplier and user.has_organization:
                queryset = queryset.filter(supplier=user.organization)
                supplier_stock_filter = models.Q(
                    stocks__warehouse__supplier=user.organization
                )
                total_quantity = Coalesce(
                    Sum("stocks__quantity", filter=supplier_stock_filter), Value(0)
                )
                total_reserved = Coalesce(
                    Sum("stocks__reserved_quantity", filter=supplier_stock_filter),
                    Value(0),
                )

                return queryset.annotate(
                    available_quantity=total_quantity - total_reserved,
                    quantity=total_quantity,
                    reserved_quantity=total_reserved,
                )
            else:
                all_total_quantity = Coalesce(Sum("stocks__quantity"), Value(0))
                all_total_reserved = Coalesce(
                    Sum("stocks__reserved_quantity"), Value(0)
                )
                return queryset.annotate(
                    available_quantity=all_total_quantity - all_total_reserved,
                )

        if self.action == "retrieve":
            if user.is_supplier and user.has_organization:
                queryset = queryset.filter(supplier=user.organization)
                return queryset.prefetch_related(
                    Prefetch(
                        "stocks",
                        queryset=Stock.objects.filter(
                            warehouse__supplier=user.organization
                        ).select_related("warehouse"),
                    )
                )
            else:
                return queryset.prefetch_related(
                    Prefetch(
                        "stocks",
                        queryset=Stock.objects.all().select_related("warehouse"),
                    )
                )

        return queryset

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user.organization)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_active:
            return Response(
                {"detail": "Товар уже деактивирован."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_active = False
        instance.save()
        return Response(
            {"detail": "Товар успешно деактивирован."}, status=status.HTTP_200_OK
        )


class WarehouseViewSet(ModelViewSet):
    queryset = Warehouse.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WarehouseListSerializer
    filterset_class = WarehouseFilter
    pagination_class = ProductNumberPagination

    lookup_field = "external_id"

    def get_permissions(self):
        base_permissions = super().get_permissions()
        if self.action in ["create", "update", "partial_update", "destroy"]:
            base_permissions.append(IsSupplierAdminOwner())
        return base_permissions

    def get_queryset(self):
        queryset = self.queryset.filter(is_active=True)
        user = self.request.user
        if user.is_buyer and user.has_organization:
            queryset = queryset.select_related("supplier")
        else:
            queryset = queryset.filter(supplier=user.organization).annotate(
                products_count=Count("stocks__product", distinct=True)
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return WarehouseCreateUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user.organization)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {"detail": "Склад успешно деактивирован."}, status=status.HTTP_200_OK
        )


class StockViewSet(UpdateModelMixin, ReadOnlyModelViewSet):
    queryset = Stock.objects.all().select_related("warehouse")
    serializer_class = StockListSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupplierAdminOwner | IsSupplierManagerOwner | IsWarehouseManagerOwner,
    ]
    pagination_class = StockNumberPagination

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "partial_update":
            return [
                (
                    permissions.IsAuthenticated
                    & (IsSupplierAdminOwner | IsWarehouseManagerOwner)
                )()
            ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "partial_update":
            return StockUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(warehouse__supplier=user.organization)
        queryset = queryset.annotate(
            available_quantity=F("quantity") - F("reserved_quantity")
        )
        return queryset

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        updated_instance = self.get_queryset().get(pk=instance.pk)
        return Response(StockListSerializer(updated_instance).data)

    @action(detail=False, methods=["get"])
    def reports(self, request):
        queryset = self.get_queryset()

        report_data = queryset.aggregate(
            products_count=Count("product"),
            total_quantity=Sum("quantity"),
            total_reserved=Sum("reserved_quantity"),
            total_available=Sum("quantity") - Sum("reserved_quantity"),
        )

        serializer = StockReportsSerializer(report_data)
        return Response(serializer.data)


class PriceListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplierAdminRole]
    queryset = PriceListImport.objects.all()

    def post(self, request):
        pass


class PriceListRetrieveAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplierAdminRole]
    queryset = PriceListImport.objects.all()

    def get(self, request, external_id):
        pass
