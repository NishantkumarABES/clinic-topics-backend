from django.db import models

class Status(models.TextChoices):
    PENDING = "pending", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"

class AccessLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INSTITUTIONAL = "institutional", "Institutional"
    PHYSICIANS = "physicians", "Verified Physicians"
    PRIVATE = "private", "Private"

class CopyrightStatus(models.TextChoices):
    OPEN = "open", "Open Access / Public Domain"
    AUTHOR = "author", "Author Owned"
    INSTITUTIONAL = "institutional", "Institutional License"
    PUBLISHER = "publisher", "Publisher Authorization"
    FAIR_USE = "fair_use", "Educational Fair Use"

class BookType(models.TextChoices):
    TEXTBOOK = "textbook", "Textbook"
    HANDBOOK = "handbook", "Handbook"
    GUIDELINE = "guideline", "Guideline"
    REVIEW = "review", "Review Article"

