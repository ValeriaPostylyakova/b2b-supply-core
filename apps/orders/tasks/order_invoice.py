import logging
from venv import logger

from billiard import SoftTimeLimitExceeded
from celery import shared_task
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML

from apps.orders.models import DocumentTypeChoices, FileDocument, Order
from config.storages import PrivateMediaStorage

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(IOError, ConnectionError),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    soft_time_limit=60,
    time_limit=75,
)
def generate_order_invoice(self, order_id: int):
    logger.info("Старт генерации счета для заказа #%s", order_id)

    try:
        if FileDocument.objects.filter(
            order_id=order_id, document_type=DocumentTypeChoices.INVOICE
        ).exists():
            logger.warning(
                "Счет для заказа #%s уже существует. Пропуск генерации.", order_id
            )
            return None

        order = Order.objects.get(id=order_id)
        items = order.items.all()
        context = {"order": order, "items": items}

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

        logger.info(
            "Счет для заказа #%s успешно сгенерирован. Doc ID: %s", order_id, doc.id
        )
        return doc.id

    except SoftTimeLimitExceeded:
        logger.error(
            "Превышено время генерации PDF для заказа #%s (Таймаут 60с)", order_id
        )
        return None

    except Exception as exc:
        logger.error(
            "Критическая ошибка при генерации счета для заказа #%s",
            order_id,
            exc_info=True,
        )
        raise exc
