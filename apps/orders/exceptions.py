from rest_framework import status
from rest_framework.exceptions import APIException


class InsufficientStock(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "INSUFFICIENT_STOCK"

    def __init__(self, product_sku, available, requested):
        detail = {
            "code": self.default_code,
            "detail": f"Недостаточно товара на складе {product_sku}",
            "available_quantity": available,
            "requested_quantity": requested,
        }
        super().__init__(detail=detail)
