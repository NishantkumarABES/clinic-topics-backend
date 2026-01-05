from django.db import models
from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from decimal import Decimal


class DoctorProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )

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



    # ---------- Section Completion Flags ----------

    overview_completed = models.BooleanField(default=False)
    professional_completed = models.BooleanField(default=False)
    license_completed = models.BooleanField(default=False)
    practice_completed = models.BooleanField(default=False)
    availability_completed = models.BooleanField(default=False)
    about_completed = models.BooleanField(default=False)

    locked_sections = models.JSONField(default=list)

    def is_fully_verified(self):
        return self.user.state == "active"
    
    def is_doctor_profile_complete(profile):
        return all([
            profile.specialization,
            profile.years_of_experience,
            profile.license_number,
            profile.clinic_name,
            profile.available_days,
            profile.available_time_slots,
        ])
    
    def is_section_locked(self, section):
        return section in self.locked_sections


    @property
    def is_verified_badge(self):
        return self.user.state == "active"

    def __str__(self):
        return f"DoctorProfile({self.user.full_name})"

class PatientProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    # ---------- Personal & Contact ----------
    blood_group = models.CharField(max_length=5, blank=True)
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
    emergency_contact_phone = models.CharField(max_length=15, blank=True)

    # ---------- Insurance ----------
    insurance_provider = models.CharField(max_length=255, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_coverage_details = models.TextField(blank=True)

    # ---------- Section Completion Flags ----------
    personal_completed = models.BooleanField(default=False)
    medical_completed = models.BooleanField(default=False)
    emergency_completed = models.BooleanField(default=False)
    insurance_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"PatientProfile({self.user.full_name})"

