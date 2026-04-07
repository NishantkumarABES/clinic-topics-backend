from django.urls import path
from apps.appointments.views import (
    DoctorListView, DoctorDetailView, AppointmentLandingView, AppointmentCategoryListCreateView, AppointmentCategoryDetailView
)

urlpatterns = [
    path("landing/", AppointmentLandingView.as_view(), name="appointment-landing"),
    path("doctors/", DoctorListView.as_view(), name="doctor-list"),
    path("doctors/<uuid:doctor_id>/", DoctorDetailView.as_view(), name="doctor-detail"),

    path("admin/categories/", AppointmentCategoryListCreateView.as_view(), name="appointment-category-list-create"),
    path("admin/categories/<int:id>/", AppointmentCategoryDetailView.as_view(), name="appointment-category-detail"),
]
