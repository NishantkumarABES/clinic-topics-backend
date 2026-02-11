from django.urls import path
from apps.IDI.views import (
    AdminIDIListCreateAPIView, AdminIDIUpdateAPIView, IDIListAPIView, IDIDetailAPIView, AdminIDIExtractAPIView
)

urlpatterns = [
    # Admin endpoints (requires IsAdminUser)
    path("admin/idi/", AdminIDIListCreateAPIView.as_view()),
    path("admin/idi/<uuid:idi_id>/", AdminIDIUpdateAPIView.as_view()),
    path("admin/idi/extract/", AdminIDIExtractAPIView.as_view()),

    # User endpoints (requires IsAuthenticated) - only published drugs
    path("idi/", IDIListAPIView.as_view(), name="idi-list"),
    path("idi/<uuid:idi_id>/", IDIDetailAPIView.as_view(), name="idi-detail"),
]