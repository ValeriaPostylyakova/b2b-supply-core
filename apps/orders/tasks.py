from celery import shared_task
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML

from apps.orders.models import DocumentTypeChoices, FileDocument, Order
from config.storages import PrivateMediaStorage


@shared_task
def generate_invoice(order_id: int):
    order = Order.objects.get(id=order_id)
    items = order.items.all()
    context = {
        "order": order,
        "items": items,
    }

    html_string = render_to_string("orders/invoice_template.html", context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    file_name = f"invoices/invoice_{order.id}.pdf"
    original_name = f"Счет-заказ №{order.id}.pdf"

    private_storage = PrivateMediaStorage()
    storage_key = private_storage.save(file_name, ContentFile(pdf_bytes))

    doc = FileDocument.objects.create(
        order=order,
        document_type=DocumentTypeChoices.INVOICE,
        storage_key=storage_key,
        original_name=original_name,
        content_type="application/pdf",
        size=len(pdf_bytes),
    )

    return doc.id
