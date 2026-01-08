import os
from config.settings.base import *
import dj_database_url

DEBUG = False
FRONTEND_BASE_URL = "http://localhost:3000"
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
OTP_EXPIRY_MINUTES = 5

DATABASES["default"] = dj_database_url.parse(
    os.getenv('DATABASE_URL'),
    conn_max_age=600,
)

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "cloudinary_storage.storage.StaticHashedCloudinaryStorage",
    },
}
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}

# Workaround for django-cloudinary-storage Django 6.0 compatibility
# The package checks for STATICFILES_STORAGE which is removed in Django 6.0
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "clinic-topics-backend.onrender.com",
    "*.onrender.com",
    "*.ngrok-free.app",
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
