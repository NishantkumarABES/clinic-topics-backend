import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from apps.accounts.models import User

ONLINE_TIMEOUT = 180  # Increased from 60 → 3 minutes


class CallSignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        url_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        if str(self.user.id) != url_user_id:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Mark user online at connection
        await self.mark_user_online(self.user.id)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        await self.mark_user_offline(self.user.id)

    async def receive(self, text_data):
        """
        Any message received from frontend acts as heartbeat.
        Frontend should send a small ping every ~30 seconds.
        """
        # Refresh online presence TTL
        await self.mark_user_online(self.user.id)

        # Optional: handle custom ping payloads if needed
        # Example frontend message: {"type": "ping"}
        # Currently no further handling required.
        return

    async def send_signal(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    # ===== Presence Helpers =====

    @database_sync_to_async
    def mark_user_online(self, user_id):
        cache.set(f"user_online_{user_id}", True, timeout=ONLINE_TIMEOUT)

        User.objects.filter(id=user_id).update(
            is_online=True,
            last_seen=timezone.now()
        )

    @database_sync_to_async
    def mark_user_offline(self, user_id):
        cache.delete(f"user_online_{user_id}")

        User.objects.filter(id=user_id).update(
            is_online=False,
            last_seen=timezone.now()
        )
