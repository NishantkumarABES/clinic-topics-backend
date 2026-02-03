from config.settings.base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
DEFAULT_FROM_EMAIL = "nishant543099@gmail.com"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "clinic_topics"),
        "USER": os.getenv("DB_USER", "clinic_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "FwpCL7p52w8N"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}