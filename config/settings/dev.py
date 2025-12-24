from config.settings.base import *
import dj_database_url

DEBUG = True
FRONTEND_BASE_URL = "http://localhost:3000"
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
OTP_EXPIRY_MINUTES = 5
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DATABASES["default"] = dj_database_url.parse(
    "postgresql://postgres_render:oRF5IVpoP8MK4fnyEbwPsjw35z281Q0g@dpg-d55ufc63jp1c73a3oa4g-a/clinic_topics",
    conn_max_age=600,
)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "clinic-topics-backend.onrender.com",
]

