from django.db import models
from django.utils.text import slugify

from apps.accounts.models import User
from apps.articles.constants import ArticleType, Status
from core.models import TimeStampedUUIDModel


class Article(TimeStampedUUIDModel):
    title = models.CharField(max_length=500)
    slug = models.SlugField(unique=True, blank=True)

    article_type = models.CharField(
        max_length=40,
        choices=ArticleType.choices
    )

    speciality = models.CharField(
        max_length=40, blank=True, null=True
    )

    authors = models.JSONField(
        help_text="List of author names"
    )

    institution = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    abstract = models.TextField()

    introduction = models.TextField(blank=True)
    methods = models.TextField(blank=True)
    results = models.TextField(blank=True)
    discussion = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)

    pdf_file = models.FileField(
        upload_to="articles/pdfs/",
        blank=True, null=True
    )

    year = models.PositiveIntegerField()
    upload_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    rejection_reason = models.TextField(
        blank=True, null=True
    )

    # engagement counters
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-upload_date"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["upload_date"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:200]
            slug = base_slug
            counter = 1

            while Article.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Bookmark(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )

    class Meta:
        unique_together = ("user", "article")

    def __str__(self):
        return f"{self.user} -> {self.article}"
