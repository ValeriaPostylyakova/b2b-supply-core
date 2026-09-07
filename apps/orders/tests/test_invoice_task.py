import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.models import DocumentTypeChoices, FileDocument, Order
from apps.orders.tasks.order_invoice import generate_order_invoice


@pytest.mark.django_db
class TestInvoiceCeleryTask:
    @pytest.fixture
    def setup_order(self):
        from apps.organizations.models import Organization

        buyer = Organization.objects.create(name="Buyer", type="BUYER")
        supplier = Organization.objects.create(name="Supplier", type="SUPPLIER")

        return Order.objects.create(
            external_id=uuid.uuid4(),
            buyer=buyer,
            supplier=supplier,
            status=Order.StatusChoices.CONFIRMED,
            total_amount=1000,
            items_count=1,
        )

    @patch("apps.orders.tasks.order_invoice.HTML")
    @patch("apps.orders.tasks.order_invoice.PrivateMediaStorage")
    def test_generate_order_invoice_success(
        self, mock_storage_cls, mock_html_cls, setup_order
    ):
        order = setup_order

        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-1.4 mock content"
        mock_html_cls.return_value = mock_html_instance

        mock_storage_instance = MagicMock()
        mock_storage_instance.save.return_value = "private/invoices/mock_invoice_1.pdf"
        mock_storage_cls.return_value = mock_storage_instance

        doc_id = generate_order_invoice.run(order_id=order.id)

        assert doc_id is not None

        doc = FileDocument.objects.get(id=doc_id)
        assert doc.order == order
        assert doc.storage_key == "private/invoices/mock_invoice_1.pdf"
        assert doc.size == len(b"%PDF-1.4 mock content")

        mock_storage_instance.save.assert_called_once()

    @patch("apps.orders.tasks.order_invoice.HTML")
    @patch("apps.orders.tasks.order_invoice.PrivateMediaStorage")
    def test_generate_order_invoice_idempotency(
        self, mock_storage_cls, mock_html_cls, setup_order
    ):
        order = setup_order

        FileDocument.objects.create(
            order=order,
            document_type=DocumentTypeChoices.INVOICE,
            storage_key="existing_key.pdf",
            original_name="existing.pdf",
            content_type="application/pdf",
            size=123,
        )

        doc_id = generate_order_invoice.run(order_id=order.id)

        assert doc_id is None
        assert FileDocument.objects.filter(order=order).count() == 1
        mock_html_cls.assert_not_called()
