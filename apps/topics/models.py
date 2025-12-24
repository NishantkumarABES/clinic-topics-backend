import uuid
from django.db import models
from apps.accounts.models import User

class TopicCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to="topics/categories/", null=True, blank=True)

    class Meta:
        db_table = "topic_categories"
        ordering = ["title"]

    def __str__(self):
        return self.title

class Topic(models.Model):
    AUDIENCE_CHOICES = (
        ("doctor", "Doctor"),
        ("general", "General"),
    )

    FORMAT_CHOICES = (
        ("1", "PDF"),
        ("2", "External Link"),
        ("3", "Video"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()

    category = models.ForeignKey(
        TopicCategory,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    topic_audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES
    )

    format = models.CharField(
        max_length=2,
        choices=FORMAT_CHOICES
    )

    external_url = models.URLField(blank=True, null=True)
    pdf = models.FileField(upload_to="topics/pdf/", blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    publishing_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "topics"
        ordering = ["-publishing_time"]

    def __str__(self):
        return self.title

class TopicImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="topics/images/")

    class Meta:
        db_table = "topic_images"