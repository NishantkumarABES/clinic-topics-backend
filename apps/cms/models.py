from django.db import models
from django.conf import settings
from core.models import TimeStampedUUIDModel

class PageType(models.TextChoices):
    PRIVACY_POLICY = "privacy_policy", "Privacy Policy"
    TERMS = "terms_conditions", "Terms & Conditions"
    ABOUT = "about_us", "About Us"
    COOKIE = "cookie_policy", "Cookie Policy"


class StaticPage(models.Model):
    page_type = models.CharField(
        max_length=50,
        choices=PageType.choices,
        unique=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.page_type


class StaticPageVersion(TimeStampedUUIDModel):
    page = models.ForeignKey(
        StaticPage,
        related_name="versions",
        on_delete=models.CASCADE
    )
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField()  # HTML / Markdown
    is_published = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("page", "version")
        ordering = ["-version"]

    def __str__(self):
        return f"{self.page.page_type} v{self.version}"

class ContactUsSubmission(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    message = models.TextField()

    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Us Submission"
        verbose_name_plural = "Contact Us Submissions"

    def __str__(self):
        return f"{self.name} - {self.email}"