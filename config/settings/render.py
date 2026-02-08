import os
from config.settings.base import *
import dj_database_url

DEBUG = True
OTP_EXPIRY_MINUTES = 5

DATABASES["default"] = dj_database_url.parse(
    os.getenv('DATABASE_URL'),
    conn_max_age=600,
)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")

AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None   # recommended by django-storages
AWS_QUERYSTRING_AUTH = False  # private files via signed URLs
# Don't set AWS_S3_CUSTOM_DOMAIN when using querystring_auth=True
# Custom domain bypasses signed URL generation, causing 403 errors
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400", "ACL": "public-read"}
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "querystring_auth": False,
        },
    },
    "private": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "querystring_auth": True,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "clinic-topics-backend.onrender.com",
    "*.onrender.com",
    "*.ngrok-free.app",
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
