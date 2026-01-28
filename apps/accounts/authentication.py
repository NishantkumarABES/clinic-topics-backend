from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.accounts.constants import UserState


class LifecycleJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if user.state in (
            UserState.DELETED
        ):
            raise AuthenticationFailed("User account is not active")

        return user
