from django.utils import timezone
from firebase_admin import messaging
from external.firebase.utils import messaging as fcm_messaging
from apps.accounts.models import UserDevice


def send_push_notification(user, title: str, body: str, data: dict = None):
    devices = UserDevice.objects.filter(user=user, is_active=True)

    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens
    )

    response = messaging.send_each_for_multicast(message)

    # Handle invalid tokens
    for idx, result in enumerate(response.responses):
        if not result.success:
            # deactivate invalid token
            UserDevice.objects.filter(
                device_token=tokens[idx]
            ).update(is_active=False)

    # Update last_seen_at for valid deliveries
    UserDevice.objects.filter(
        device_token__in=tokens,
        is_active=True
    ).update(last_seen_at=timezone.now())

    return {
        "success": True,
        "sent": response.success_count,
        "failed": response.failure_count
    }

def send_silent_push_notification(user, data: dict):
    devices = UserDevice.objects.filter(user=user, is_active=True)

    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    message = messaging.MulticastMessage(
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
        apns=messaging.APNSConfig(
            headers={
                "apns-push-type": "background",
                "apns-priority": "5"
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(content_available=True)
            )
        )
    )

    response = messaging.send_each_for_multicast(message)

    return {
        "success": True,
        "sent": response.success_count,
        "failed": response.failure_count
    }

def send_call_silent_push(user, data: dict):
    devices = UserDevice.objects.filter(user=user, is_active=True)
    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    message = messaging.MulticastMessage(
        data={k: str(v) for k, v in data.items()},
        tokens=tokens,

        # Android immediate delivery
        android=messaging.AndroidConfig(
            priority="high", ttl=0
        ),

        # iOS immediate silent background delivery
        apns=messaging.APNSConfig(
            headers={
                "apns-push-type": "background",
                "apns-priority": "10"
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(content_available=True)
            )
        )
    )

    response = messaging.send_each_for_multicast(message)

    # Deactivate invalid tokens
    for idx, r in enumerate(response.responses):
        if not r.success:
            UserDevice.objects.filter(device_token=tokens[idx]).update(is_active=False)

    UserDevice.objects.filter(
        device_token__in=tokens,
        is_active=True
    ).update(last_seen_at=timezone.now())

    return {
        "success": True,
        "sent": response.success_count,
        "failed": response.failure_count
    }