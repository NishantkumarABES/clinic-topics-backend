from django.db import models

class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    REVIEW = "review", "In Review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"