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
MEDIA_URL = "/media/"

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

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}

FRONTEND_BASE_URL = "http://localhost:3000"
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
OTP_EXPIRY_MINUTES = 5
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "clinic-topics-backend.onrender.com",
    "*.ngrok-free.app",
]
