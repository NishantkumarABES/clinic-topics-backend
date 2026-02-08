import os
from config.settings.base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "clinic_topics"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "admin"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")

AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None   # recommended by django-storages
AWS_QUERYSTRING_AUTH = True  # private files via signed URLs
# Don't set AWS_S3_CUSTOM_DOMAIN when using querystring_auth=True
# Custom domain bypasses signed URL generation, causing 403 errors
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"


STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
OTP_EXPIRY_MINUTES = 5
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "clinic-topics-backend.onrender.com",
    "*.ngrok-free.app",
]
