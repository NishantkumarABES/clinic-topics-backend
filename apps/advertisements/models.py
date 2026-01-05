from django.db import models
from core.models import TimeStampedUUIDModel


class AdvertisementStatus(models.TextChoices):
    ENABLED = 'enabled', 'Enabled'
    DISABLED = 'disabled', 'Disabled'


class Advertisement(TimeStampedUUIDModel):
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    image = models.ImageField(upload_to='advertisements/')
    status = models.CharField(
        max_length=10,
        choices=AdvertisementStatus.choices,
        default=AdvertisementStatus.ENABLED
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'

    def __str__(self):
        return self.title
