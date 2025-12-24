from django.urls import path
from apps.appointments.views import DoctorListView, DoctorDetailView

urlpatterns = [
    path("doctors/", DoctorListView.as_view()),
    path("doctors/<uuid:doctor_id>/", DoctorDetailView.as_view()),
]
