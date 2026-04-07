from django.db import models

class AppointmentCategory(models.Model):
    key = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    image = models.ImageField(upload_to="appointment/categories/")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.label