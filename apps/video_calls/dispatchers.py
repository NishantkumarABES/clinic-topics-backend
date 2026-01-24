from apps.video_calls.signals import send_call_signal, is_user_online
from apps.notifications.services import send_call_silent_push


def dispatch_call_event(user, data: dict):
    """
    Sends call event via WebSocket if online, otherwise silent push.
    """
    data["experienceId"] = "@clinictopics-org/clinictopics"
    data["scopeKey"] = "@clinictopics-org/clinictopics"

    if is_user_online(str(user.id)):
        send_call_signal(user_id=str(user.id), data=data)
        return {"via": "websocket"}

    send_call_silent_push(user=user, data=data)
    return {"via": "push"}