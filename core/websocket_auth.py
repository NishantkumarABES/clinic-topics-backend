from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.accounts.authentication import LifecycleJWTAuthentication


@database_sync_to_async
def get_user_from_token(token):
    jwt_auth = LifecycleJWTAuthentication()
    validated = jwt_auth.get_validated_token(token)
    user = jwt_auth.get_user(validated)
    return user


class JWTAuthMiddleware:
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
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
