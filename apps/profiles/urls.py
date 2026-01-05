from django.urls import path
from apps.profiles.views import (
    DoctorProfileView, DoctorLicenseUploadView, PatientProfileView, AdminDoctorListView,
    DoctorOverviewUpdateView, DoctorProfessionalUpdateView, DoctorLicenseUpdateView, DoctorPracticeUpdateView,
    DoctorAvailabilityUpdateView, DoctorAboutUpdateView, PatientPersonalUpdateView, PatientMedicalUpdateView,
    PatientEmergencyUpdateView, PatientInsuranceUpdateView
)

urlpatterns = [
    # Doctor APIs Endpoints
    path("doctor-profile/", DoctorProfileView.as_view()),
    path("doctor-profile/overview/", DoctorOverviewUpdateView.as_view()),
    path("doctor-profile/professional/", DoctorProfessionalUpdateView.as_view()),
    path("doctor-profile/license/", DoctorLicenseUpdateView.as_view()),
    path("doctor-profile/practice/", DoctorPracticeUpdateView.as_view()),
    path("doctor-profile/availability/", DoctorAvailabilityUpdateView.as_view()),
    path("doctor-profile/about/", DoctorAboutUpdateView.as_view()),
    path("doctor-profile/license/", DoctorLicenseUploadView.as_view()),
    
    # Patient APIs Endpoints
    path("patient-profile/", PatientProfileView.as_view()),
    path("patient-profile/personal/", PatientPersonalUpdateView.as_view()),
    path("patient-profile/medical/", PatientMedicalUpdateView.as_view()),
    path("patient-profile/emergency/", PatientEmergencyUpdateView.as_view()),
    path("patient-profile/insurance/", PatientInsuranceUpdateView.as_view()),
    
    # Admin APIs Endpoints
    path("doctors/", AdminDoctorListView.as_view()),
]
