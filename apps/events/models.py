import pytz
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

from core.models import TimeStampedUUIDModel
from apps.events.constants import EventType, EventFormat, EventStatus


class Event(TimeStampedUUIDModel):
    # --- Core fields ---
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)

    event_type = models.CharField(
        max_length=30,
        choices=EventType.CHOICES
    )
    specialization = models.CharField(max_length=100,  null=True)
    # Dates and times split to match frontend DTO
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata"
    )
    format = models.CharField(
        max_length=20,
        choices=EventFormat.CHOICES
    )

    is_free = models.BooleanField(default=True)
    registration_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )

    is_certificate_available = models.BooleanField(default=False)
    agenda = models.TextField(null=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    event_link = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=EventStatus.CHOICES,
        default="upcoming"
    )

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # --- Derived fields ---
    duration_minutes = models.PositiveIntegerField(default=0)

    # --- Validation & Auto-calculation ---
    def clean(self):
        if self.is_free and self.registration_fee != 0:
            raise ValidationError("Free events must have registration_fee = 0")
        if not self.is_free and self.registration_fee <= 0:
            raise ValidationError("Paid events must have registration_fee > 0")
        # Date logic
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date")
        # Time logic (only if same day)
        if self.start_date == self.end_date:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after start time")
        
    def calculate_status(self):
        if self.status == EventStatus.CANCELLED:
            return EventStatus.CANCELLED

        if not all([self.start_date, self.start_time, self.end_date, self.end_time]):
            return EventStatus.UPCOMING

        try:
            tz = pytz.timezone(self.timezone or "Asia/Kolkata")
        except Exception:
            tz = pytz.timezone("Asia/Kolkata")

        start_dt = datetime.combine(self.start_date, self.start_time)
        end_dt = datetime.combine(self.end_date, self.end_time)

        start_dt = tz.localize(start_dt)
        end_dt = tz.localize(end_dt)

        now = timezone.now().astimezone(tz)

        if now < start_dt:
            return EventStatus.UPCOMING
        elif start_dt <= now <= end_dt:
            return EventStatus.ONGOING
        return EventStatus.COMPLETED

    def save(self, *args, **kwargs):
        # Calculate duration
        if all([self.start_date, self.start_time, self.end_date, self.end_time]):
            start_dt = datetime.combine(self.start_date, self.start_time)
            end_dt = datetime.combine(self.end_date, self.end_time)
            self.duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

        # Single source of truth
        self.status = self.calculate_status()

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

# ----------------------------
# Speaker Model
# ----------------------------

class EventSpeaker(TimeStampedUUIDModel):
    event = models.ForeignKey(
        Event,
        related_name="speakers",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=150)
    title = models.CharField(max_length=150)
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="event_speakers/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.event.title})"

# ----------------------------
# Event Image Model
# ----------------------------

class EventImage(TimeStampedUUIDModel):
    event = models.ForeignKey(
        Event,
        related_name="images",
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="event_images/")

    def __str__(self):
        return f"Image for {self.event.title}"





