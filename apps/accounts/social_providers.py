import os, requests
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from jwt.algorithms import RSAAlgorithm
from jose import jwt

class SocialUser:
    def __init__(self, provider, provider_user_id, email=None):
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.email = email

APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
APPLE_JWKS_CACHE_KEY = "apple_jwks_cache"
APPLE_JWKS_TTL = 60 * 60 * 24  # 24 hours


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
def get_apple_public_keys():
    # Try cache first
    keys = cache.get(APPLE_JWKS_CACHE_KEY)
    if keys:
        return keys

    # Fetch from Apple if not cached
    try:
        response = requests.get(APPLE_PUBLIC_KEY_URL, timeout=5)
        if response.status_code != 200:
            raise AuthenticationFailed("Unable to fetch Apple public keys")

        keys = response.json()
        cache.set(APPLE_JWKS_CACHE_KEY, keys, APPLE_JWKS_TTL)
        return keys

    except requests.RequestException:
        # If Apple is down but cache exists, use stale cache
        cached = cache.get(APPLE_JWKS_CACHE_KEY)
        if cached:
            return cached
        raise AuthenticationFailed("Apple public key service unreachable")

def verify_apple_token(token):
    APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
    APPLE_KEY_ID    = os.getenv("APPLE_KEY_ID")

    if not all([APPLE_CLIENT_ID, APPLE_KEY_ID]):
        raise AuthenticationFailed("Missing Apple environment configuration")

    try:
        # 1. Load keys (cached)
        apple_keys = get_apple_public_keys()

        # 2. Read token header
        unverified_header = jwt.get_unverified_header(token)
        token_kid = unverified_header.get("kid")

        if not token_kid:
            raise AuthenticationFailed("Invalid Apple token: missing key id")

        # 3. Enforce expected signing key
        if token_kid != APPLE_KEY_ID:
            raise AuthenticationFailed("Unexpected Apple signing key")

        # 4. Locate matching public key
        public_key = None
        for key in apple_keys.get("keys", []):
            if key.get("kid") == token_kid:
                public_key = RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise AuthenticationFailed("Apple public key not found")

        # 5. Verify token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=APPLE_CLIENT_ID,
            issuer="https://appleid.apple.com"
        )

        provider_user_id = claims.get("sub")
        email = claims.get("email")

        if not provider_user_id:
            raise AuthenticationFailed("Invalid Apple token: missing subject")

        return SocialUser(
            provider="apple",
            provider_user_id=provider_user_id,
            email=email
        )

    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Apple token expired")

    except jwt.JWTError as e:
        raise AuthenticationFailed(f"Invalid Apple token: {str(e)}")

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