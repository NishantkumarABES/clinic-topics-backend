import os, firebase_admin
from firebase_admin import credentials, messaging


FCM_SERVICE_ACCOUNT_JSON = {
    "type": os.getenv('FIRE_BASE_ACCOUNT_TYPE'),
    "project_id": os.getenv('FIRE_BASE_PROJECT_ID'),
    "private_key_id": os.getenv('FIRE_BASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIRE_BASE_PRIVATE_KEY'),
    "client_email": os.getenv('FIRE_BASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIRE_BASE_CLIENT_ID'),
    "auth_uri": os.getenv('FIRE_BASE_AUTH_URI'),
    "token_uri": os.getenv('FIRE_BASE_TOKEN_URI'),  
    "auth_provider_x509_cert_url": os.getenv('FIRE_BASE_AUTH_PROVIDER_X509_CERT_URL'),
    "client_x509_cert_url": os.getenv('FIRE_BASE_CLIENT_X509_CERT_URL'),
    "universe_domain": os.getenv('FIRE_BASE_UNIVERSE_DOMAIN')
}

# Initialize only once
if not firebase_admin._apps:
    cred = credentials.Certificate(FCM_SERVICE_ACCOUNT_JSON)
    firebase_admin.initialize_app(cred)
