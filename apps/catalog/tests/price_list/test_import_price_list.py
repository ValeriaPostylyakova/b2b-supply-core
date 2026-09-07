import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from apps.catalog.models import (
    PriceListImport,
    Product,
    Stock,
    Warehouse,
)
from apps.catalog.tasks import process_price_list_import_task
from apps.organizations.models import Organization


def create_in_memory_excel(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    return file_stream


@pytest.mark.django_db
class TestPriceListImportTask:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.supplier = Organization.objects.create(
            name="Global Supplier", type="SUPPLIER"
        )

        self.warehouse = Warehouse.objects.create(
            name="Main-Moscow", supplier=self.supplier, address="Moscow", is_active=True
        )

        self.import_record = PriceListImport.objects.create(
            supplier=self.supplier,
            original_name="prices.xlsx",
            storage_key="media/imports/prices.xlsx",
            status="PENDING",
        )

    @patch("apps.catalog.tasks.price_list.PrivateMediaStorage")
    def test_import_success(self, mock_storage_cls):

        headers = ["sku", "name", "price", "warehouse", "quantity"]
        rows = [
            ["SKU-NEW-1", "Product One", 150.50, "Main-Moscow", 50],
            ["SKU-NEW-2", "Product Two", 299.00, "Main-Moscow", 100],
        ]
        excel_file = create_in_memory_excel(headers, rows)

        mock_storage_instance = MagicMock()
        mock_storage_instance.open.return_value = excel_file
        mock_storage_cls.return_value = mock_storage_instance

        result_message = process_price_list_import_task.run(
            import_id=self.import_record.id
        )

        self.import_record.refresh_from_db()
        assert self.import_record.status == "COMPLETED"
        assert self.import_record.total_rows == 2
        assert self.import_record.success_rows == 2
        assert self.import_record.error_rows == 0

        assert Product.objects.filter(supplier=self.supplier, sku="SKU-NEW-1").exists()
        prod2 = Product.objects.get(supplier=self.supplier, sku="SKU-NEW-2")
        assert prod2.price == Decimal("299.00")

        stock2 = Stock.objects.get(product=prod2, warehouse=self.warehouse)
        assert stock2.quantity == 100

    @patch("apps.catalog.tasks.price_list.PrivateMediaStorage")
    def test_import_completed_with_errors(self, mock_storage_cls):
        headers = ["sku", "name", "price", "warehouse", "quantity"]
        rows = [
            ["SKU-OK", "Good Product", 100.00, "Main-Moscow", 10],
            [
                "SKU-BAD",
                "Bad Product",
                200.00,
                "NON-EXISTENT-WAREHOUSE",
                20,
            ],
        ]
        excel_file = create_in_memory_excel(headers, rows)

        mock_storage_instance = MagicMock()
        mock_storage_instance.open.return_value = excel_file
        mock_storage_cls.return_value = mock_storage_instance

        process_price_list_import_task.run(import_id=self.import_record.id)

        self.import_record.refresh_from_db()
        assert self.import_record.status == "COMPLETED_WITH_ERRORS"
        assert self.import_record.total_rows == 2
        assert self.import_record.success_rows == 1
        assert self.import_record.error_rows == 1

        assert Product.objects.filter(sku="SKU-OK").exists()
        assert not Product.objects.filter(sku="SKU-BAD").exists()

    @patch("apps.catalog.tasks.price_list.PrivateMediaStorage")
    def test_import_failed_missing_headers(self, mock_storage_cls):
        headers = ["wrong_column_1", "wrong_column_2"]
        rows = [["data1", "data2"]]
        excel_file = create_in_memory_excel(headers, rows)

        mock_storage_instance = MagicMock()
        mock_storage_instance.open.return_value = excel_file
        mock_storage_cls.return_value = mock_storage_instance

        process_price_list_import_task.run(import_id=self.import_record.id)

        self.import_record.refresh_from_db()
        assert self.import_record.status == "FAILED"
