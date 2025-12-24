from django.db import models
from core.models import TimeStampedUUIDModel
from config.settings.base import AUTH_USER_MODEL


class EventType(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Event(TimeStampedUUIDModel):
    EVENT_MODE_CHOICES = [
        ("live", "Live"),
        ("recorded", "Recorded"),
        ("hybrid", "Hybrid"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()

    event_type = models.ForeignKey(
        EventType,
        on_delete=models.PROTECT,
        related_name="events"
    )

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    mode = models.CharField(
        max_length=20,
        choices=EVENT_MODE_CHOICES
    )

    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    max_participants = models.PositiveIntegerField(null=True, blank=True)

    is_certificate_available = models.BooleanField(default=False)

    recording_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class EventRegistration(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("registered", "Registered"),
        ("attended", "Attended"),
        ("cancelled", "Cancelled"),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations"
    )
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="registered"
    )

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"{self.user} → {self.event}"
