from django.contrib import admin
from apps.profiles.models import DoctorProfile, PatientProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specializations", "verification_status")
    list_filter = ("verification_status",)
    actions = ["approve_doctors"]

    def approve_doctors(self, request, queryset):
        queryset.update(verification_status="approved")


admin.site.register(PatientProfile)
