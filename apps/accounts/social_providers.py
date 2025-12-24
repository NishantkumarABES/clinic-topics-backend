import os, requests
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt

MICROSOFT_JWKS_URL = "https://login.microsoftonline.com/organizations/discovery/v2.0/keys"

class SocialUser:
    def __init__(self, provider, provider_user_id, email=None):
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.email = email


# -------- GOOGLE --------
def verify_google_token(token):
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": token},
        timeout=5
    )

    if resp.status_code != 200:
        raise AuthenticationFailed("Invalid Google token")

    data = resp.json()
    return SocialUser(
        provider="google",
        provider_user_id=data["sub"],
        email=data.get("email")
    )


# -------- FACEBOOK --------
def verify_facebook_token(token):
    resp = requests.get(
        "https://graph.facebook.com/me",
        params={"access_token": token, "fields": "email"},
        timeout=5
    )

    if resp.status_code != 200:
        raise AuthenticationFailed("Invalid Facebook token")

    data = resp.json()
    return SocialUser(
        provider="facebook",
        provider_user_id=data["id"],
        email=data.get("email")
    )



# -------- APPLE --------
def verify_apple_token(token):
    # Apple token verification is more complex (JWT + public keys).
    # For Phase-1, assume frontend passes verified claims.
    # This function is intentionally isolated.
    raise AuthenticationFailed(
        "Apple token verification must be implemented with JWT validation"
    )


social_provider_verification = {
    "google": verify_google_token,
    "facebook": verify_facebook_token,
    "apple": verify_apple_token,
}












# # -------- MICROSOFT --------
# def verify_microsoft_token(id_token):
#     try:
#         jwks = requests.get(MICROSOFT_JWKS_URL, timeout=5).json()
#     except Exception:
#         raise AuthenticationFailed("Unable to fetch Microsoft public keys")

#     try:
#         claims = jwt.decode(
#             id_token, jwks,
#             algorithms=["RS256"],
#             audience=os.getenv("MICROSOFT_CLIENT_ID"),
#             issuer="https://login.microsoftonline.com/common/v2.0"
#         )
#     except Exception:
#         raise AuthenticationFailed("Invalid Microsoft ID token")

#     email = claims.get("email") or claims.get("preferred_username")

#     if not email:
#         raise AuthenticationFailed("Email not found in Microsoft token")

#     return SocialUser(
#         provider="microsoft",
#         provider_user_id=claims["oid"],
#         email=email,
#     )