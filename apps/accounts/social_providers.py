import os, requests
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt

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
    APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"

    try:
        # Fetch Apple's public keys
        response = requests.get(APPLE_PUBLIC_KEY_URL, timeout=5)
        if response.status_code != 200:
            raise AuthenticationFailed("Unable to fetch Apple public keys")

        apple_keys = response.json()

        # Decode the JWT header to get the key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        key_id = unverified_header.get("kid")

        if not key_id:
            raise AuthenticationFailed("Invalid Apple token: missing key ID")

        # Find the matching public key
        public_key = None
        for key in apple_keys.get("keys", []):
            if key.get("kid") == key_id:
                public_key = key
                break

        if not public_key:
            raise AuthenticationFailed("Apple public key not found")

        # Verify and decode the token
        # Apple's audience should be your app's client ID
        apple_client_id = os.getenv("APPLE_CLIENT_ID")
        if not apple_client_id:
            raise AuthenticationFailed("Apple Client ID not configured")

        # Decode and verify the JWT
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=apple_client_id,
            issuer="https://appleid.apple.com"
        )

        # Extract user information
        # Apple's 'sub' claim is the unique user identifier
        provider_user_id = claims.get("sub")
        email = claims.get("email")

        if not provider_user_id:
            raise AuthenticationFailed("Invalid Apple token: missing user ID")

        return SocialUser(
            provider="apple",
            provider_user_id=provider_user_id,
            email=email
        )

    except jwt.JWTError as e:
        raise AuthenticationFailed(f"Invalid Apple token: {str(e)}")
    except requests.RequestException as e:
        raise AuthenticationFailed(f"Failed to verify Apple token: {str(e)}")
    except Exception as e:
        raise AuthenticationFailed(f"Apple authentication error: {str(e)}")


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