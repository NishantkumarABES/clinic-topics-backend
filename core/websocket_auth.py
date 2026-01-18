from urllib.parse import parse_qs
from channels.db import database_sync_to_async


@database_sync_to_async
def get_user_from_token(token):
    # Import inside function AFTER Django is ready
    from rest_framework_simplejwt.authentication import JWTAuthentication
    
    jwt_auth = JWTAuthentication()
    validated = jwt_auth.get_validated_token(token)
    user = jwt_auth.get_user(validated)
    return user


class JWTAuthMiddleware:
    """
    JWT Authentication middleware for Django Channels.
    Usage:
    ws://localhost:8000/ws/calls/<user_id>/?token=<JWT>
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope["query_string"].decode()
        params = parse_qs(query_string)

        token_list = params.get("token")

        if token_list:
            try:
                scope["user"] = await get_user_from_token(token_list[0])
            except Exception:
                scope["user"] = None
        else:
            scope["user"] = None

        return await self.inner(scope, receive, send)
