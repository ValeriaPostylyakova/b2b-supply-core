from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import IsSupplierAdminRole
from apps.catalog.api.serializers.price_list import (
    PriceListImportCreateSerializer,
    PriceListImportStatusSerializer,
    PriceListPresignedUrlRequestSerializer,
)
from apps.catalog.models.price_list import PriceListImport
from apps.catalog.services.price_list import PriceListImportService
from apps.organizations.api.permissions import (
    IsSupplierAdminOwner,
)


class PriceListPresignedUrlAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplierAdminRole()]

    def post(self, request):
        serializer = PriceListPresignedUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data["file_name"]
        upload_data = PriceListImportService.generate_pricelist_upload_data(file_name)
        return Response(upload_data, status=status.HTTP_200_OK)


class PriceListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplierAdminRole]

    def post(self, request):
        serializer = PriceListImportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = request.user.organization

        import_external_id = PriceListImportService.process_price_list_import(
            storage_key=serializer.validated_data["storage_key"],
            original_name=serializer.validated_data["original_name"],
            organization_id=organization.id,
        )

        return Response(
            {
                "id": import_external_id,
                "status": PriceListImport.Status.PENDING,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PriceListRetrieveAPIView(RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplierAdminOwner]
    serializer_class = PriceListImportStatusSerializer
    queryset = PriceListImport.objects.all()
    lookup_field = "external_id"
