from django.contrib import admin
from apps.profiles.models import DoctorProfile, PatientProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "license_number")


admin.site.register(PatientProfile)
