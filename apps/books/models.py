from django.db import models
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.books.constants import BookType, CopyrightStatus, AccessLevel, Status, PaymentMethod
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

    speciality = models.CharField(max_length=100, null=True, blank=True)

    book_type = models.CharField(
        max_length=20,
        choices=BookType.choices,
        default=BookType.TEXTBOOK
    )

    description = models.TextField(blank=True)

    # File
    file = models.FileField(
        upload_to="books/files/",
    )
    book_cover = models.ImageField(
        upload_to="books/covers/",
        blank=True, null=True
    )

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
    rating_count = models.PositiveIntegerField(default=0)

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
    price = models.PositiveIntegerField(
        default=0,
        help_text="Price in paise. 0 means free."
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason provided by admin when rejecting the book."
    )
    is_deleted = models.BooleanField(default=False)

    def update_rating(self):
        qs = self.ratings.aggregate(
            avg=Avg("rating"),
            count=models.Count("id")
        )

        self.rating = round(qs["avg"] or 0, 1)
        self.rating_count = qs["count"]
        self.save(update_fields=["rating", "rating_count"])
        
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["publication_year"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return self.title

class BookPurchase(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="book_purchases"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE,
        related_name="purchases"
    )

    # Razorpay
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=100, blank=True, null=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD
    )

    amount = models.PositiveIntegerField()  # in paise
    currency = models.CharField(max_length=10, default="INR")

    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user} → {self.book} ({'PAID' if self.is_paid else 'PENDING'})"

class BookRating(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="book_ratings"
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "book")
        indexes = [
            models.Index(fields=["book"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.book} ({self.rating})"

class BookCategory(models.Model):
    key = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    image = models.ImageField(upload_to="books/categories/")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.label