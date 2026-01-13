from django.db import models
from core.models import TimeStampedUUIDModel


class AdvisoryStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'


class AdvisoryMember(TimeStampedUUIDModel):
    """Advisory board member model."""
    
    full_name = models.CharField(max_length=255)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        null=True,
        blank=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    specialization = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='advisory/', null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=AdvisoryStatus.choices,
        default=AdvisoryStatus.ACTIVE
    )

    class Meta(TimeStampedUUIDModel.Meta):
        db_table = "advisory_members"
        ordering = ["-created_at"]
        verbose_name = "Advisory Member"
        verbose_name_plural = "Advisory Members"
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.specialization}"
