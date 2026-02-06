from django.urls import path
from apps.profiles.views import ProfileMeView, DoctorRatingView

urlpatterns = [
    path("profile/me/", ProfileMeView.as_view()),
    path("doctors/<uuid:doctor_id>/ratings/", DoctorRatingView.as_view(), name="doctor-ratings"),
]

