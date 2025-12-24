from config.settings.base import *

DEBUG = True
FRONTEND_BASE_URL = "http://localhost:3000"
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
OTP_EXPIRY_MINUTES = 5


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "clinic_topics",
        "USER": "postgres-render",
        "PASSWORD": "oRF5IVpoP8MK4fnyEbwPsjw35z281Q0g",
        "HOST": "dpg-d55ufc63jp1c73a3oa4g-a.postgres.render.com",
        "PORT": "5432",
    }
}

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]

