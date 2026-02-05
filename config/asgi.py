import os
from dotenv import load_dotenv, find_dotenv
# Load env file first
load_dotenv(find_dotenv(".env", raise_error_if_not_found=True), override=True)
# Set settings module BEFORE any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
# Now safe to import Django/Channels
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.video_calls.urls import websocket_urlpatterns
from core.websocket_auth import JWTAuthMiddleware
# Django ASGI app

# Protocol router
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
