from rest_framework import status
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_details = response.data

        error_code = "api_error"
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "validation_error"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "not_authenticated"

        custom_response_data = {
            "success": False,
            "data": None,
            "error": {
                "code": error_code,
                "message": "Произошла ошибка при обработке запроса.",
                "details": error_details
            }
        }

        response.data = custom_response_data
    return response
