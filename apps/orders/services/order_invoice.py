from celery.result import AsyncResult
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.orders.api.serializers.order import FileDocumentSerializer
from apps.orders.models.file_documents import FileDocument
from apps.orders.models.order import Order
from apps.orders.tasks.order_invoice import generate_order_invoice


class InvoiceService:
    @staticmethod
    def generate_invoice(order_id, order_status):
        if order_status != Order().StatusChoices.CONFIRMED:
            raise ValidationError(
                {
                    "detail": "Счет может быть сформирован только для подтвержденного заказа."
                }
            )

        task = generate_order_invoice.delay(order_id)
        return task.id

    @staticmethod
    def get_invoice_status(task_id: str) -> dict:
        task_result = AsyncResult(task_id)
        status = task_result.status

        if status in ["PENDING", "RECEIVED"]:
            return {"status": status}

        if status == "STARTED":
            return {"status": "Processing", "message": "Документ формируется"}

        if status == "SUCCESS":
            doc_id = task_result.result
            document = get_object_or_404(FileDocument, id=doc_id)
            serializer = FileDocumentSerializer(document)

            return {"status": "Completed", "document": serializer.data}

        if status == "FAILURE":
            return {
                "status": "Failed",
                "detail": "Произошла ошибка при генерации PDF.",
                "error": str(task_result.info),
            }

        return {"status": status}
