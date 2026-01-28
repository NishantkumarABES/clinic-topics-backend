from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedUUIDModel
from decimal import Decimal

from apps.accounts.models import User
from apps.accounts.constants import UserRole
from apps.profiles.constants import BloodGroup


class DoctorProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )
    profile_photo = models.FileField(upload_to="doctor_photos/", null=True, blank=True)

    # ---------- Overview / Identity ----------
    credentials = models.CharField(
        max_length=255, null=True, blank=True
    )  # e.g. MD, MS, MBBS

    specialization = models.CharField(max_length=100, null=True, blank=True)
    years_of_experience = models.PositiveIntegerField()

    # languages_spoken = models.JSONField(null=True, blank=True)

    # ---------- Professional Details ----------
    qualifications = models.JSONField(null=True, blank=True)
    areas_of_expertise = models.JSONField(null=True, blank=True)
    conditions_treated = models.JSONField(null=True, blank=True)

    professional_memberships = models.JSONField(null=True, blank=True)
    publications = models.JSONField(null=True, blank=True)

    # ---------- Medical License ----------
    license_number = models.CharField(max_length=100)
    medical_council = models.CharField(max_length=255, null=True, blank=True)
    registration_numbers = models.JSONField(null=True, blank=True)
    license_issue_year = models.PositiveIntegerField(null=True, blank=True)
    license_document = models.FileField(upload_to="licenses/")

    # ---------- Practice Information ----------
    clinic_name = models.CharField(max_length=255, null=True, blank=True)
    clinic_address = models.TextField(null=True, blank=True)

    clinic_location = models.JSONField(
        null=True, blank=True
    )  # {lat, lng}

    clinic_photos = models.JSONField(
        null=True, blank=True
    )  # list of image URLs/keys

    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    premium_online_fee = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal("0.00"),
        null=True, blank=True
    )

    consultation_duration_minutes = models.PositiveIntegerField(
        null=True, blank=True
    )

    # ---------- Availability ----------
    available_days = models.JSONField(null=True, blank=True)
    available_time_slots = models.JSONField(null=True, blank=True)

    # ---------- About ----------
    bio = models.TextField(blank=True)
    awards = models.TextField(blank=True)
    website_url = models.URLField(null=True, blank=True)

    def average_rating(self):
        return self.user.ratings_received.aggregate(
            avg=models.Avg("rating")
        )["avg"] or 0

    def is_complete(self):
        return all([
            self.specialization,
            self.years_of_experience is not None,
            self.license_number,
            self.license_document,
            self.consultation_fee is not None,
            self.premium_online_fee is not None,
            self.website_url is not None,
        ])


    def __str__(self):
        return f"DoctorProfile({self.user.full_name})"

class PatientProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )
    profile_photo = models.FileField(upload_to="patient_photos/", null=True, blank=True)
    # ---------- Personal & Contact ----------
    blood_group = models.CharField(
        max_length=3, choices=BloodGroup.choices,
        blank=True, null=True
    )
    address = models.TextField(blank=True)

    # ---------- Medical Information ----------
    medical_history = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    previous_surgeries = models.TextField(blank=True)
    family_medical_history = models.TextField(blank=True)

    # ---------- Emergency Contact ----------
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contant_country_code = models.CharField(max_length=10, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)

    # ---------- Insurance ----------
    insurance_provider = models.CharField(max_length=255, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_coverage_details = models.TextField(blank=True)


    def __str__(self):
        return f"PatientProfile({self.user.full_name})"

class DoctorRating(TimeStampedUUIDModel):
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ratings_received",
        limit_choices_to={"role": UserRole.DOCTOR}
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ratings_given",
        limit_choices_to={"role": UserRole.PATIENT}
    )

    second_opinion_doctor_request = models.OneToOneField(
        "second_opinion.SecondOpinionDoctorRequest",
        on_delete=models.CASCADE,
        related_name="rating",
        null=True,
        blank=True
    )

    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rating for Dr. {self.doctor.get_full_name()} - {self.rating}/5"
