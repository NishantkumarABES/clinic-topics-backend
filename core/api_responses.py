from drf_yasg import openapi


# ============================================
# STANDARD RESPONSE SCHEMA HELPER
# ============================================
def _standard_response_schema(description: str, with_data: bool = False, data_schema=None):
    """Helper to create consistent response schemas with {detail, data, success} format."""
    properties = {
        "detail": openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Success status"),
    }
    if with_data:
        properties["data"] = data_schema or openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Response data",
            nullable=True
        )
    return openapi.Response(
        description=description,
        schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties=properties)
    )


# ============================================
# SUCCESS RESPONSES
# ============================================
SUCCESS_200 = _standard_response_schema("Success", with_data=True)
SUCCESS_201 = _standard_response_schema("Created successfully", with_data=True)
SUCCESS_NO_DATA_200 = _standard_response_schema("Success")
SUCCESS_NO_DATA_201 = _standard_response_schema("Created successfully")


# ============================================
# ERROR RESPONSES
# ============================================
UNAUTHORIZE_401 = openapi.Response(
    description="Unauthorized",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "detail": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
        },
    ),
)

BAD_REQUEST_400 = openapi.Response(
    description="Bad Request",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "detail": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
        },
    ),
)

NOT_FOUND_404 = openapi.Response(
    description="Not Found",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "detail": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
        },
    ),
)

FORBIDDEN_403 = openapi.Response(
    description="Forbidden",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "detail": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
        },
    ),
)

TOO_MANY_REQUESTS_429 = openapi.Response(
    description="Too Many Requests",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "detail": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
            "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
        },
    ),
)
