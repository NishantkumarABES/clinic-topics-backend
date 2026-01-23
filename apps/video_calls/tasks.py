from django.utils import timezone
from datetime import timedelta
from celery import shared_task

from apps.video_calls.models import VideoCallSession
from apps.video_calls.constants import CallStatus
from apps.video_calls.dispatchers import dispatch_call_event


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
            dispatch_call_event(
                participant,
                {"event": "call_missed", "call_id": str(call.id)}
            )



        
