import os, requests, time, json
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt, jwk
from jose.exceptions import JWTError, JWTClaimsError, ExpiredSignatureError


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

def generate_apple_client_secret():
    team_id = os.getenv("APPLE_TEAM_ID")
    client_id = os.getenv("APPLE_CLIENT_ID")
    key_id = os.getenv("APPLE_KEY_ID")
    private_key_path = os.getenv("APPLE_PRIVATE_KEY_PATH")

    if not all([team_id, client_id, key_id, private_key_path]):
        raise AuthenticationFailed("Missing Apple OAuth configuration")

    with open(private_key_path, "r") as f:
        private_key = f.read()

    now = int(time.time())

    payload = {
        "iss": team_id,
        "iat": now,
        "exp": now + (60 * 60 * 24 * 180),  # 180 days max allowed by Apple
        "aud": "https://appleid.apple.com",
        "sub": client_id,
    }

    headers = {
        "kid": key_id,
        "alg": "ES256",
    }

    client_secret = jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers=headers
    )

    return client_secret

def exchange_apple_code_for_token(code):
    client_id = os.getenv("APPLE_CLIENT_ID")
    client_secret = generate_apple_client_secret()

    response = requests.post(
        "https://appleid.apple.com/auth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=10
    )

    if response.status_code != 200:
        raise AuthenticationFailed(
            f"Apple token exchange failed: {response.text}"
        )

    return response.json()

# -------- APPLE --------
def get_apple_public_keys():
    # Try cache first (with graceful fallback if Redis is unavailable)
    try:
        keys = cache.get(APPLE_JWKS_CACHE_KEY)
        if keys:
            return keys
    except Exception:
        # Cache unavailable (e.g., Redis not running), continue without cache
        pass

    # Fetch from Apple if not cached or cache unavailable
    try:
        response = requests.get(APPLE_PUBLIC_KEY_URL, timeout=5)
        if response.status_code != 200:
            raise AuthenticationFailed("Unable to fetch Apple public keys")

        keys = response.json()
        
        # Try to cache the keys (ignore errors if cache is unavailable)
        try:
            cache.set(APPLE_JWKS_CACHE_KEY, keys, APPLE_JWKS_TTL)
        except Exception:
            pass  # Cache unavailable, continue without caching
            
        return keys

    except requests.RequestException:
        # If Apple is down, try to get from cache as fallback
        try:
            cached = cache.get(APPLE_JWKS_CACHE_KEY)
            if cached:
                return cached
        except Exception:
            pass  # Cache unavailable
        raise AuthenticationFailed("Apple public key service unreachable")

def verify_apple_token(authorization_code):

    token_response = exchange_apple_code_for_token(
        authorization_code
    )

    identity_token = token_response.get("id_token")

    if not identity_token:
        raise AuthenticationFailed("Apple did not return identity token")

    # Get Apple's public keys (JWKS)
    apple_keys = get_apple_public_keys()

    # Get the key ID from the token header
    try:
        header = jwt.get_unverified_header(identity_token)
    except JWTError as e:
        raise AuthenticationFailed(f"Invalid Apple identity token format: {str(e)}")

    kid = header.get("kid")
    if not kid:
        raise AuthenticationFailed("Apple identity token missing key ID")

    # Find the matching public key
    public_key_data = None
    for key in apple_keys.get("keys", []):
        if key.get("kid") == kid:
            public_key_data = key
            break

    if not public_key_data:
        # Key not found, try refreshing the cache
        cache.delete(APPLE_JWKS_CACHE_KEY)
        apple_keys = get_apple_public_keys()
        for key in apple_keys.get("keys", []):
            if key.get("kid") == kid:
                public_key_data = key
                break

    if not public_key_data:
        raise AuthenticationFailed("Apple public key not found for token")

    # Construct the RSA public key using python-jose
    try:
        public_key = jwk.construct(public_key_data, algorithm="RS256")
    except Exception as e:
        raise AuthenticationFailed(f"Failed to construct Apple public key: {str(e)}")

    # Decode and verify the token
    try:
        claims = jwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=os.getenv("APPLE_CLIENT_ID"),
            issuer="https://appleid.apple.com"
        )
    except ExpiredSignatureError:
        raise AuthenticationFailed("Apple identity token has expired")
    except JWTClaimsError as e:
        raise AuthenticationFailed(f"Apple token claims validation failed: {str(e)}")
    except JWTError as e:
        raise AuthenticationFailed(f"Apple token verification failed: {str(e)}")

    return SocialUser(
        provider="apple",
        provider_user_id=claims["sub"],
        email=claims.get("email")
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