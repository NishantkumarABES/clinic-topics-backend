from django.db import models
from django.contrib.postgres.fields import ArrayField

from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.jobs.constants import *


class JobPost(TimeStampedUUIDModel):
    # ---- Ownership & lifecycle ----
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="job_posts"
    )

    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING_REVIEW,
        db_index=True
    )

    # ---- Core identity ----
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)

    summary = models.TextField()
    responsibilities = models.TextField()
    qualifications = models.TextField()

    # ---- Classification ----
    workplace_type = models.CharField(
        max_length=20,
        choices=WorkplaceType.choices
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices
    )

    job_function = models.CharField(
        max_length=30,
        choices=JobFunction.choices
    )

    specialty = models.CharField(max_length=255)

    seniority_level = models.CharField(
        max_length=20,
        choices=SeniorityLevel.choices
    )

    # ---- Location ----
    location = models.CharField(max_length=255)
    remote_region = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # ---- Experience & credentials ----
    experience_years = models.PositiveIntegerField()

    required_degrees = models.CharField(max_length=255)
    required_registrations = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # ---- Skills ----
    must_have_skills = ArrayField(
        base_field=models.CharField(max_length=100),
        default=list,
    )

    nice_to_have_skills = ArrayField(
        base_field=models.CharField(max_length=100),
        default=list,
    )

    # ---- Compensation ----
    salary_range = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    benefits = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # ---- Compliance ----
    work_authorization = models.CharField(
        max_length=30,
        choices=WorkAuthorization.choices,
        blank=True,
        null=True
    )

    background_checks_required = models.BooleanField(default=False)

    # ---- Application flow ----
    apply_method = models.CharField(
        max_length=30,
        choices=ApplyMethod.choices
    )

    apply_target = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL or email depending on apply_method"
    )

    application_deadline = models.DateField(
        blank=True,
        null=True
    )

    contact_person = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # ---- Visibility & discovery ----
    visibility = models.CharField(
        max_length=30,
        choices=Visibility.choices
    )

    tags = ArrayField(
        base_field=models.CharField(max_length=100),
        default=list,
    )

    # ---- Misc ----
    notes = models.TextField(blank=True, null=True)

    agreed_to_terms = models.BooleanField(default=False)
    agreed_at = models.DateTimeField(blank=True, null=True, editable=False)


    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["job_function"]),
            models.Index(fields=["visibility"]),
        ]

    def __str__(self):
        return f"{self.title} @ {self.company_name}"

    def clean(self):
        """
        Model-level validation for conditional rules.
        """
        from django.core.exceptions import ValidationError

        if self.apply_method in [
            ApplyMethod.EXTERNAL_LINK,
            ApplyMethod.EMAIL
        ] and not self.apply_target:
            raise ValidationError(
                "apply_target is required for external link or email applications."
            )

        if not self.agreed_to_terms:
            raise ValidationError(
                "You must confirm permission to post this job."
            )
