import uuid
from django.db import models
from apps.accounts.models import User
from core.models import TimeStampedUUIDModel

class Topic(TimeStampedUUIDModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    image = models.URLField()
    source_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    publishing_time = models.DateTimeField()
    publish_status = models.BooleanField(default=False)

    class Meta:
        db_table = "topics"
        ordering = ["-publishing_time"]

    def __str__(self):
        return self.title



