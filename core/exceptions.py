from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError


def extract_first_error(detail, parent_key=""):
    if isinstance(detail, list):
        return str(detail[0])

    if isinstance(detail, dict):
        field, value = next(iter(detail.items()))

        # remove DRF non_field_errors noise
        if field == "non_field_errors":
            return extract_first_error(value)

        full_key = f"{parent_key}.{field}" if parent_key else field
        return f"{full_key}: {extract_first_error(value)}"

    return str(detail)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    if isinstance(exc, ValidationError):
        first_error = extract_first_error(response.data)

        response.data = {
            "detail": first_error,
            "data": None,
            "success": False,
        }
        return response

    # Optional — unify ALL error responses
    response.data = {
        "detail": response.data.get("detail", "Something went wrong"),
        "data": None,
        "success": False,
    }

    return response
