from django.db import models

class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEW = "review", "In Review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"