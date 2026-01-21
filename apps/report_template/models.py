from django.db import models
from apps.accounts.models import User
from core.models import TimeStampedUUIDModel




def clinic_logo_upload_path(instance, filename):
    return f"report_templates/{instance.doctor.id}/logo/{filename}"


def doctor_signature_upload_path(instance, filename):
    return f"report_templates/{instance.doctor.id}/signature/{filename}"


class ReportTemplate(TimeStampedUUIDModel):
    doctor = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name="report_template"
    )

    # Branding
    clinic_logo = models.ImageField(
        upload_to=clinic_logo_upload_path,
        null=True, blank=True
    )

    doctor_signature = models.ImageField(
        upload_to=doctor_signature_upload_path,
        null=True, blank=True
    )

    # Clinic Information
    clinic_name = models.CharField(max_length=255)
    address = models.TextField()

    # Contact details
    phone_number = models.CharField(max_length=20)
    website = models.URLField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255)

    class Meta:
        db_table = "report_templates"
        verbose_name = "Report Template"
        verbose_name_plural = "Report Templates"

    def __str__(self):
        return f"{self.clinic_name} - {self.doctor}"
