from celery.result import AsyncResult

from apps.orders.api.serializers.order import FileDocumentSerializer
from apps.orders.models.file_documents import FileDocument
from apps.orders.models.order import Order
from apps.orders.tasks.order_invoice import generate_invoice


class InvoiceService:
    @staticmethod
    def generate_invoice(order_id):
        order = Order.objects.get(id=order_id)
        if order.status != Order().StatusChoices.CONFIRMED:
            raise ValueError("Данный заказ не может быть выставлен счет")

        task = generate_invoice.delay(order.id)
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
            try:
                document = FileDocument.objects.get(id=doc_id)
                serializer = FileDocumentSerializer(document)

                return {"status": "Completed", "document": serializer.data}
            except FileDocument.DoesNotExist:
                raise ValueError("Документ не найден")

        if status == "FAILURE":
            return {
                "status": "Failed",
                "detail": "Произошла ошибка при генерации PDF.",
                "error": str(task_result.info),
            }

        return {"status": status}
