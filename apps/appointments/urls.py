from django.urls import path
from apps.appointments.views import DoctorListView, DoctorDetailView, AppointmentLandingView, AppointmentCategoryCreateView

urlpatterns = [
    path("landing/", AppointmentLandingView.as_view(), name="appointment-landing"),
    path("doctors/", DoctorListView.as_view(), name="doctor-list"),
    path("doctors/<uuid:doctor_id>/", DoctorDetailView.as_view(), name="doctor-detail"),

    path("categories/", AppointmentCategoryCreateView.as_view(), name="appointment-category-create"),
]
