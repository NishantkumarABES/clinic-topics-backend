from django.db import models

from apps.accounts.models import User
from apps.articles.constants import ArticleType, Status
from core.models import TimeStampedUUIDModel



class Article(TimeStampedUUIDModel):
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="uploaded_articles",
        blank=True, null=True
    )

    title = models.CharField(max_length=500)

    article_type = models.CharField(
        max_length=40,
        choices=ArticleType.choices
    )

    speciality = models.CharField(
        max_length=40,
        blank=True,
        null=True
    )

    authors = models.CharField(max_length=500)

    institution = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    abstract = models.TextField()
    # journal_name = models.CharField(max_length=255, blank=True)
    # keywords = models.CharField(max_length=255, blank=True)

    # introduction = models.TextField(blank=True)
    # methods = models.TextField(blank=True)
    # results = models.TextField(blank=True)
    # discussion = models.TextField(blank=True)
    # conclusion = models.TextField(blank=True)
    content = models.TextField(blank=True, null=True)

    # pdf_file = models.FileField(
    #     upload_to="articles/pdfs/",
    #     blank=True, null=True
    # )

    # year = models.PositiveIntegerField()
    publication_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    # is_featured = models.BooleanField(default=False)

    # Soft delete
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["article_type"]),
        ]
    
    @property
    def citation(self):
        authors = self.authors
        year = self.publication_date.year if self.publication_date else ""
        return f"{authors}. {self.title}. {year}."


    def __str__(self):
        return self.title

class Bookmark(TimeStampedUUIDModel):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="article_bookmarks"
    )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )

    class Meta:
        unique_together = ("user", "article")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["article"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.article}"


# class Author(models.Model):
#     article = models.ForeignKey(
#         Article,
#         related_name="article_authors",
#         on_delete=models.CASCADE
#     )
#     first_name = models.CharField(max_length=120)
#     middle_name = models.CharField(max_length=120, blank=True)
#     last_name = models.CharField(max_length=120)

#     affiliation = models.CharField(max_length=255, blank=True)

#     order = models.PositiveIntegerField()  # preserves author order

#     class Meta:
#         ordering = ["order"]
#         indexes = [
#             models.Index(fields=["article"]),
#         ]

#     def __str__(self):
#         return f"{self.first_name} {self.last_name}"
