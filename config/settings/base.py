import os
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab

DEBUG = True
SECRET_KEY = os.getenv('SECRET_KEY')

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "accept",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    'django.contrib.postgres',
    "cloudinary",
    "django.contrib.staticfiles",
    "corsheaders",
    "storages",
    # third-party
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "channels",

    # local
    "apps.accounts.app.AccountsConfig",
    "apps.profiles.app.ProfilesConfig",
    "apps.commerce.app.CommerceConfig",
    "apps.events.app.EventsConfig",
    "apps.topics.app.TopicsConfig",
    "apps.analytics.app.AnalyticsConfig",
    "apps.cms.app.CMSConfig",
    "apps.advertisements.app.AdvertisementsConfig",
    "apps.IDI.app.IDIConfig",
    "apps.advisory.app.AdvisoryConfig",
    "apps.second_opinion.app.SecondOpinionConfig",
    "apps.appointments.app.AppointmentsConfig",
    "apps.video_calls.app.VideoCallsConfig",
    "apps.report_template.app.ReportTemplateConfig",
    "apps.notifications.app.NotificationsConfig",

    # MY REPOSITE's APP
    "apps.books.app.BooksConfig",
    "apps.jobs.app.JobsConfig",
    "apps.articles.app.ArticlesConfig",
    "apps.videos.app.VideosConfig",

    "core.app.CoreConfig",
]

ASGI_APPLICATION = "config.asgi.application"

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),

    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "clinic_topics",
        "USER": "postgres",
        "PASSWORD": "admin",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header. Example: Bearer <access_token>",
        }
    },
    "USE_SESSION_AUTH": False,
}

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "admin-staging-api.clinictopics.com"
]

BASE_DIR = Path(__file__).resolve().parents[2]

STATIC_URL = "/static/"
# For production (collectstatic)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "accounts.User"
ROOT_URLCONF = "config.urls"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
OTP_EXPIRY_MINUTES = 5
AGORA_TOKEN_EXPIRY=3600
# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')



CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "expire-unanswered-calls": {
        "task": "apps.video_calls.tasks.expire_unanswered_calls",
        "schedule": 30.0,
    },

    "mark-inactive-users": {
        "task": "apps.accounts.tasks.mark_inactive_users",
        "schedule": crontab(hour=3, minute=0),  # every day at 3 AM
    },
    
    "update-event-statuses": {
        "task": "apps.events.tasks.update_event_statuses",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
}
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL