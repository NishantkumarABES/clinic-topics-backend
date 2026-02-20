from django.db import models
from apps.accounts.models import User
from apps.articles.constants import Status  
from core.models import TimeStampedUUIDModel


class Video(TimeStampedUUIDModel):
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_videos",
        blank=True,
        null=True
    )

    # Basic Info
    title = models.CharField(max_length=500)
    description = models.TextField()
    Institution = models.CharField(max_length=500)
    speciality = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Video File (stores object key in S3)
    video_file = models.FileField(
        upload_to="videos/"
    )

    thumbnail = models.ImageField(
        upload_to="videos/thumbnails/",
        blank=True,
        null=True
    )

    duration_seconds = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    # Moderation Workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    # Analytics
    like_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    # Soft Delete
    is_deleted = models.BooleanField(default=False)
    allow_download = models.BooleanField(default=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["speciality"]),
        ]

    def __str__(self):
        return self.title

class VideoBookmark(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="video_bookmarks"
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )

    class Meta:
        unique_together = ("user", "video")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["video"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.video}"

class VideoLike(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="video_likes"
    )

    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="likes"
    )

    class Meta:
        unique_together = ("user", "video")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["video"]),
        ]

    def __str__(self):
        return f"{self.user} liked {self.video}"