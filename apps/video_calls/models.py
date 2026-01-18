from django.db import models

from apps.video_calls.constants import CallStatus
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from core.models import TimeStampedUUIDModel

class VideoCallSession(TimeStampedUUIDModel):
    channel_name = models.CharField(max_length=255, unique=True)

    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_calls",
        limit_choices_to={"role": UserRole.DOCTOR}
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_calls",
        limit_choices_to={"role": UserRole.PATIENT}
    )

    status = models.CharField(
        max_length=20,
        choices=CallStatus.choices,
        default=CallStatus.INITIATED
    )

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "video_call_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel_name} ({self.status})"