from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.jobs.constants import *



class JobPost(TimeStampedUUIDModel):
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
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

    job_function = models.CharField(
        max_length=30,
        choices=JobFunction.choices
    )

    speciality = models.CharField(max_length=255)

    seniority_level = models.CharField(
        max_length=20,
        choices=SeniorityLevel.choices
    )

    experience = models.CharField(
        max_length=100,
        help_text="E.g., 5+ years",
        blank=True,
        null=True
    )

    # ✅ Unified Rich Text Description Field
    job_description = models.TextField(
        help_text="Full job description including summary, responsibilities, qualifications, and benefits (supports rich text).",
        blank=True, null=True
    )

    must_have_skills = models.TextField()

    salary_range = models.CharField(max_length=150, blank=True, null=True)

    required_degrees = models.CharField(max_length=255)

    application_deadline = models.DateField(null=True, blank=True)

    recruiter_name = models.CharField(max_length=255, blank=True)

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
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma separated tags. Example: cardiology, remote, urgent"
    )

    # Analytics
    views = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["application_deadline"]),
            models.Index(fields=["created_by"]),
        ]
    
    def check_and_mark_expired(self):
        if (
            self.status == JobPostStatus.PUBLISHED
            and self.application_deadline
            and self.application_deadline < timezone.now().date()
        ):
            self.status = JobPostStatus.EXPIRED
            self.save(update_fields=["status"])


    def __str__(self):
        return self.title

class JobApplication(TimeStampedUUIDModel):
    job = models.ForeignKey(
        JobPost, on_delete=models.CASCADE,
        related_name="applications"
    )

    applicant = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="job_applications"
    )

    # Application Form Fields
    resume = models.FileField(
        upload_to="jobs/resumes/",
        validators=[FileExtensionValidator(["pdf"])]
    )

    additional_information = models.TextField(
        help_text="Additional information provided by applicant (supports rich text).",
        blank=True,
        null=True
    )

    years_of_experience = models.CharField(max_length=50, blank=True, null=True)
    current_position = models.CharField(max_length=255, blank=True, null=True)
    current_institution = models.CharField(max_length=255, blank=True, null=True)

    notice_period = models.CharField(max_length=100, blank=True, null=True)
    expected_salary = models.CharField(max_length=150, blank=True, null=True)

    additional_document = models.FileField(
        upload_to="jobs/additional_docs/",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=JobApplicationStatus.choices,
        default=JobApplicationStatus.PENDING
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


