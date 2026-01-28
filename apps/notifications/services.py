# from django.utils import timezone
# from firebase_admin import messaging
# from external.firebase.utils import messaging as fcm_messaging
# from apps.accounts.models import UserDevice

from django.utils import timezone
from exponent_server_sdk import PushClient, PushMessage, PushServerError, DeviceNotRegisteredError, MessageTooBigError
from apps.accounts.models import UserDevice


# def send_push_notification(user, title: str, body: str, data: dict = None):
#     devices = UserDevice.objects.filter(user=user, is_active=True)

#     if not devices.exists():
#         return {"success": False, "reason": "No active devices"}

#     tokens = [d.device_token for d in devices]

#     message = messaging.MulticastMessage(
#         notification=messaging.Notification(
#             title=title,
#             body=body
#         ),
#         data={k: str(v) for k, v in (data or {}).items()},
#         tokens=tokens
#     )

#     response = messaging.send_each_for_multicast(message)

#     # Handle invalid tokens
#     for idx, result in enumerate(response.responses):
#         if not result.success:
#             # deactivate invalid token
#             UserDevice.objects.filter(
#                 device_token=tokens[idx]
#             ).update(is_active=False)

#     # Update last_seen_at for valid deliveries
#     UserDevice.objects.filter(
#         device_token__in=tokens,
#         is_active=True
#     ).update(last_seen_at=timezone.now())

#     return {
#         "success": True,
#         "sent": response.success_count,
#         "failed": response.failure_count
#     }

# def send_silent_push_notification(user, data: dict):
#     devices = UserDevice.objects.filter(user=user, is_active=True)

#     if not devices.exists():
#         return {"success": False, "reason": "No active devices"}

#     tokens = [d.device_token for d in devices]

#     message = messaging.MulticastMessage(
#         data={k: str(v) for k, v in (data or {}).items()},
#         tokens=tokens,
#         apns=messaging.APNSConfig(
#             headers={
#                 "apns-push-type": "background",
#                 "apns-priority": "5"
#             },
#             payload=messaging.APNSPayload(
#                 aps=messaging.Aps(content_available=True)
#             )
#         )
#     )

#     response = messaging.send_each_for_multicast(message)

#     return {
#         "success": True,
#         "sent": response.success_count,
#         "failed": response.failure_count
#     }

# def send_call_silent_push(user, data: dict):
    # devices = UserDevice.objects.filter(user=user, is_active=True)
    # if not devices.exists():
    #     return {"success": False, "reason": "No active devices"}

    # tokens = [d.device_token for d in devices]

    # message = messaging.MulticastMessage(
    #     data={k: str(v) for k, v in data.items()},
    #     tokens=tokens,

    #     # Android immediate delivery
    #     android=messaging.AndroidConfig(
    #         priority="high", ttl=0
    #     ),

    #     # iOS immediate silent background delivery
    #     apns=messaging.APNSConfig(
    #         headers={
    #             "apns-push-type": "background",
    #             "apns-priority": "10"
    #         },
    #         payload=messaging.APNSPayload(
    #             aps=messaging.Aps(content_available=True)
    #         )
    #     )
    # )

    # response = messaging.send_each_for_multicast(message)

    # # Deactivate invalid tokens
    # for idx, r in enumerate(response.responses):
    #     if not r.success:
    #         UserDevice.objects.filter(device_token=tokens[idx]).update(is_active=False)

    # UserDevice.objects.filter(
    #     device_token__in=tokens,
    #     is_active=True
    # ).update(last_seen_at=timezone.now())

    # return {
    #     "success": True,
    #     "sent": response.success_count,
    #     "failed": response.failure_count
    # }




expo_client = PushClient()

def send_push_notification(user, title: str, body: str, data: dict = None):
    """
    Standard visible notification.
    """
    devices = UserDevice.objects.filter(user=user, is_active=True)

    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    messages = [
        PushMessage(
            to=token,
            title=title,
            body=body,
            data={k: str(v) for k, v in (data or {}).items()},
            sound="default"
        )
        for token in tokens
    ]

    return _send_expo_messages(tokens, messages)

def send_silent_push_notification(user, data: dict):
    """
    Generic silent/background push.
    (Expo treats data-only messages as background notifications automatically.)
    """
    devices = UserDevice.objects.filter(user=user, is_active=True)

    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    messages = [
        PushMessage(
            to=token,
            data={k: str(v) for k, v in (data or {}).items()}
        )
        for token in tokens
    ]

    return _send_expo_messages(tokens, messages)

def send_call_silent_push(user, data: dict):
    """
    Used by video call dispatcher for incoming calls.
    """
    devices = UserDevice.objects.filter(user=user, is_active=True)

    if not devices.exists():
        return {"success": False, "reason": "No active devices"}

    tokens = [d.device_token for d in devices]

    messages = [
        PushMessage(
            to=token,
            data={k: str(v) for k, v in data.items()}
        )
        for token in tokens
    ]

    return _send_expo_messages(tokens, messages)

def _send_expo_messages(tokens, messages):
    """
    Shared sender with error handling and token cleanup.
    """
    success_count = 0
    failed_count = 0

    try:
        responses = expo_client.publish_multiple(messages)
    except PushServerError:
        return {"success": False, "reason": "Expo push server error"}

    for idx, response in enumerate(responses):
        if response.is_success():
            success_count += 1
            UserDevice.objects.filter(
                device_token=tokens[idx],
                is_active=True
            ).update(last_seen_at=timezone.now())
        else:
            failed_count += 1

            # Invalid Expo token → deactivate
            if isinstance(response.details, DeviceNotRegisteredError):
                UserDevice.objects.filter(
                    device_token=tokens[idx]
                ).update(is_active=False)

            # Oversized payload → ignore but counted
            if isinstance(response.details, MessageTooBigError):
                pass

    return {
        "success": True,
        "sent": success_count,
        "failed": failed_count
    }

if __name__ == "__main__":
    _send_expo_messages(tokens='ExponentPushToken[Y0bEdKB1Wele4ksiEI2iG6]', messages= 'Testing the expo message')
    