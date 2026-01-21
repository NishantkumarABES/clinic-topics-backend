from django.utils import timezone
from datetime import timedelta
from celery import shared_task

from apps.video_calls.models import VideoCallSession
from apps.video_calls.constants import CallStatus
from apps.video_calls.signals import send_call_signal, is_user_online
from apps.notifications.services import send_push_notification



@shared_task
def expire_unanswered_calls():
    expiry_time = timezone.now() - timedelta(seconds=30)

    stale_calls = VideoCallSession.objects.filter(
        status=CallStatus.INITIATED,
        created_at__lt=expiry_time
    )

    for call in stale_calls:
        call.status = CallStatus.MISSED
        call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])

        for participant in [call.doctor, call.patient]:
            send_push_notification(
                user=participant,
                title="Missed Call",
                body="You missed a call",
                data={"event": "call_missed", "call_id": str(call.id)}
            )
            if is_user_online(str(participant.id)):
                send_call_signal(
                    user_id=str(participant.id),
                    data={"event": "call_missed", "call_id": str(call.id)}
                )



        
