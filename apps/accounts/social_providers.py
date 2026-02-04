import os, requests, time
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

def verify_apple_token(authorization_code):

    token_response = exchange_apple_code_for_token(
        authorization_code
    )

    identity_token = token_response.get("id_token")

    if not identity_token:
        raise AuthenticationFailed("Apple did not return identity token")

    # reuse your existing JWKS verification
    apple_keys = get_apple_public_keys()

    header = jwt.get_unverified_header(identity_token)
    kid = header["kid"]

    public_key = None
    for key in apple_keys["keys"]:
        if key["kid"] == kid:
            public_key = RSAAlgorithm.from_jwk(key)
            break

    if not public_key:
        raise AuthenticationFailed("Apple public key not found")

    claims = jwt.decode(
        identity_token,
        public_key,
        algorithms=["RS256"],
        audience=os.getenv("APPLE_CLIENT_ID"),
        issuer="https://appleid.apple.com"
    )

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


if __name__ == "__main__":
    verify_apple_token("neyJraWQiOiJhVmVIRmFXeEFaIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoib3JnLnJlYWN0anMubmF0aXZlLmV4YW1wbGUuQ2xpbmljVG9waWNzIiwiZXhwIjoxNzcwMzA5ODYyLCJpYXQiOjE3NzAyMjM0NjIsInN1YiI6IjAwMTQwMS44ZjYwODdkNWZlZTU0N2I5OTM0YWJkN2U0YzU3NjA0Mi4wNTA4IiwiY19oYXNoIjoiX2t6eG9MREYta2VCaDZvcS16RTNCQSIsImVtYWlsIjoiYWxvay5zaW5naEBxc3N0ZWNobm9zb2Z0LmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJhdXRoX3RpbWUiOjE3NzAyMjM0NjIsIm5vbmNlX3N1cHBvcnRlZCI6dHJ1ZX0.Wp_D6FygBicPli2mW71qkvjqsDvSEsMVgIQ7lBvnR0ECLytWMmOMkS0yRZdqOjilYTSYSGBoesM-sO6p9lCD-evaUkvbQdy2zg97zzahDztOrMXCgFemp59yZMfmAakQyAPrDRHiNsZDzarczJhtd239LZvnjDigIS6K8XviK2jw0Ld7Yarb_ApWDq5cvkh12s0CDCXB-aTjW8QO6r3p27VFGsld9ncWQGoIjNEAOYoPD88ufgXEN38vO6aeT7DMwAydiZUrcHv70eXhNzqAe_9ZO_-6u0yhc94TTo8AgQL8cgP2mXU3Okcnd-w3nnaWMtWo-giry-2c4PkgKTf0Tg\r\n--0P5bATcQx3IqjJRRW1FMYXPvB7u4thNMgK9jZ7g6Lv.vZgoUgUGp2JdWYD688IoHmgyArK")









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