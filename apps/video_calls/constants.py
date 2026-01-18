from django.db import models


class CallStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    RINGING = "ringing", "Ringing"
    ACTIVE = "active", "Active"
    ENDED = "ended", "Ended"
    REJECTED = "rejected", "Rejected"
    MISSED = "missed", "Missed"