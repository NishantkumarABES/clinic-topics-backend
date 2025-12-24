# appointments/admin.py
from django.contrib import admin
from apps.appointments.models import (
    DoctorAvailability,
    AppointmentSlot,
    Appointment,
)


admin.site.register(DoctorAvailability)
admin.site.register(AppointmentSlot)
admin.site.register(Appointment)
