from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.jobs.constants import *


class JobTag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class JobPost(TimeStampedUUIDModel):
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posted_jobs"
    )

    # Core Fields
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)

    workplace_type = models.CharField(
        max_length=20,
        choices=WorkplaceType.choices
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices
    )

    job_location = models.CharField(max_length=255)
    hiring_regions = models.CharField(
        max_length=255,
        blank=True,
        help_text="Applicable if remote"
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

    experience = models.CharField(
        max_length=100,
        help_text="E.g., 5+ years",
        blank=True, null=True
    )

    # Description Blocks
    role_summary = models.TextField()
    responsibilities = models.TextField()
    qualifications = models.TextField()

    must_have_skills = models.TextField()
    nice_to_have_skills = models.TextField(blank=True)

    salary_range = models.CharField(max_length=150, blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)

    required_degrees = models.CharField(max_length=255)
    # required_registrations = models.CharField(max_length=255)

    background_checks = models.BooleanField(default=False)

    application_deadline = models.DateField(null=True, blank=True)

    recruiter_name = models.CharField(max_length=255, blank=True)

    additional_notes = models.TextField(blank=True)

    apply_method = models.CharField(
        max_length=20,
        choices=ApplyMethod.choices,
        default=ApplyMethod.PLATFORM
    )

    external_apply_link = models.URLField(blank=True, null=True)
    application_email = models.EmailField(blank=True, null=True)


    # Moderation
    status = models.CharField(
        max_length=20,
        choices=JobPostStatus.choices,
        default=JobPostStatus.DRAFT
    )

    rejection_reason = models.TextField(blank=True, null=True)

    # Tags
    tags = models.ManyToManyField(
        JobTag,
        related_name="jobs",
        blank=True
    )

    # Analytics
    views = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    application_views_count = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["application_deadline"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.title

class JobApplication(TimeStampedUUIDModel):
    job = models.ForeignKey(
        JobPost, on_delete=models.CASCADE,
        related_name="applications"
    )

    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="job_applications"
    )

    # Application Form Fields
    resume = models.FileField(
        upload_to="jobs/resumes/",
        validators=[FileExtensionValidator(["pdf"])]
    )

    cover_letter = models.TextField()

    years_of_experience = models.CharField(max_length=50)
    current_position = models.CharField(max_length=255)
    current_institution = models.CharField(max_length=255)

    notice_period = models.CharField(max_length=100)
    expected_salary = models.CharField(max_length=150)

    additional_document = models.FileField(
        upload_to="jobs/additional_docs/",
        blank=True,
        null=True
    )

    class Meta:
        unique_together = ("job", "applicant")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["applicant"]),
        ]
    
    def clean(self):
        if self.resume.size > 10 * 1024 * 1024:
            raise ValidationError("Max file size is 10MB")


    def __str__(self):
        return f"{self.applicant} → {self.job}"

class JobApplicationView(TimeStampedUUIDModel):
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="views"
    )

    viewed_by = models.ForeignKey(
        User, on_delete=models.CASCADE
    )

    class Meta:
        indexes = [
            models.Index(fields=["application"]),
        ]
