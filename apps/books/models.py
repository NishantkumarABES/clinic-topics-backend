from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.books.constants import BookType, CopyrightStatus, AccessLevel, Status
from apps.accounts.models import User
from core.models import TimeStampedUUIDModel


class Collection(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(TimeStampedUUIDModel):
    # Ownership
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="uploaded_books"
    )

    # Core metadata
    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=500)
    publisher = models.CharField(max_length=255, blank=True)
    edition = models.CharField(max_length=50)
    publication_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)]
    )


    isbn = models.CharField(max_length=20, blank=True, db_index=True)

    specialty = models.CharField(max_length=100, null=True, blank=True)

    book_type = models.CharField(
        max_length=20,
        choices=BookType.choices,
        default=BookType.TEXTBOOK
    )

    description = models.TextField(blank=True)

    # File
    file = models.FileField(upload_to="books/files/")

    # Legal & access
    copyright_status = models.CharField(
        max_length=20,
        choices=CopyrightStatus.choices,
        default=CopyrightStatus.OPEN
    )

    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.PUBLIC
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Analytics
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    views = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)

    # Curation
    is_editor_curated = models.BooleanField(default=False)

    # Collections
    collections = models.ManyToManyField(
        Collection,
        related_name="books",
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["publication_year"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return self.title
