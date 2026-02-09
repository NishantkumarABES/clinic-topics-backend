from django.db import models

class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "In Review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

class ArticleType(models.TextChoices):
    ORIGINAL_RESEARCH = "original_research", "Original Research"
    REVIEW = "review", "Review"
    CASE_REPORT = "case_report", "Case Report"
    BRIEF_COMMUNICATION = "brief_communication", "Brief Communication"