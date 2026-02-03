import os
from config.settings.base import *
import dj_database_url

DEBUG = True
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
OTP_EXPIRY_MINUTES = 5

DATABASES["default"] = dj_database_url.parse(
    os.getenv('DATABASE_URL'),
    conn_max_age=600,
)

STORAGES = {
    # Default → Images
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    # Raw files → PDFs, docs, zips
    "raw": {
        "BACKEND": "cloudinary_storage.storage.RawMediaCloudinaryStorage",
    },
    # Videos
    "video": {
        "BACKEND": "cloudinary_storage.storage.VideoMediaCloudinaryStorage",
    },
    # Static files (Whitenoise)
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"


STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"



CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
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
