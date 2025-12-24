from django.db import models
from core.models import TimeStampedUUIDModel
from apps.profiles.models import DoctorProfile
from config.settings.base import AUTH_USER_MODEL

class DoctorAvailability(TimeStampedUUIDModel):
    WEEKDAY_CHOICES = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="weekly_availability"
    )

    weekday = models.CharField(max_length=3, choices=WEEKDAY_CHOICES)

    start_time = models.TimeField()
    end_time = models.TimeField()

    is_online = models.BooleanField(default=False)

    class Meta:
        unique_together = ("doctor", "weekday", "start_time", "end_time")

class AppointmentSlot(TimeStampedUUIDModel):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="slots"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_online = models.BooleanField(default=False)
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("doctor", "date", "start_time")

class Appointment(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("booked", "Booked"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.PROTECT,
        related_name="appointments"
    )
    patient = models.ForeignKey(
        AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    slot = models.OneToOneField(
        AppointmentSlot,
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="booked"
    )

    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    is_online = models.BooleanField(default=False)

    class Meta:
        unique_together = ("doctor", "patient", "slot")

    def __str__(self):
        return f"{self.patient} → {self.doctor}"