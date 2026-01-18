from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.cache import cache


def send_call_signal(user_id, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "send_signal",
            "data": data
        }
    )

def is_user_online(user_id: str) -> bool:
    return cache.get(f"user_online_{user_id}") is True