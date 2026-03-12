import uuid
from django.db import models
from django.utils import timezone
from apps.accounts.models import User

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # who receives it (admins only in your case)
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

