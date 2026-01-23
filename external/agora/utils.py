import os, time
from django.conf import settings
from agora_token_builder import RtcTokenBuilder
from config.settings import AGORA_TOKEN_EXPIRY


def generate_agora_token(channel_name: str, uid: int):
    app_id = os.environ.get("AGORA_APP_ID")
    app_certificate = os.environ.get("AGORA_APP_CERTIFICATE")
    expiration_time_in_seconds = AGORA_TOKEN_EXPIRY

    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_name, uid, 1, privilege_expired_ts)
    return token
