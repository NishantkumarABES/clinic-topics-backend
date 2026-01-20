import uuid
from django.db import models
from apps.accounts.models import User
from core.models import TimeStampedUUIDModel

class Topic(TimeStampedUUIDModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    image = models.URLField(null=True)
    source_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    publishing_time = models.DateTimeField()
    publish_status = models.BooleanField(default=False)

    class Meta:
        db_table = "topics"
        ordering = ["-publishing_time"]

    def __str__(self):
        return self.title


class TopicTranscription(TimeStampedUUIDModel):
    """Stores transcription data and AI-generated summary for video topics"""
    topic = models.OneToOneField(
        Topic,
        on_delete=models.CASCADE,
        related_name='transcription'
    )
    sonix_media_id = models.CharField(max_length=255, unique=True)
    
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('transcribing', 'Transcribing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='preparing'
    )
    
    transcript_text = models.TextField(blank=True, null=True)
    transcript_srt = models.TextField(blank=True, null=True)
    transcript_json = models.JSONField(blank=True, null=True)
    summary_text = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "topic_transcriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transcription for {self.topic.title} - {self.status}"
