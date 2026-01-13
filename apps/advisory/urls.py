from django.urls import path
from apps.advisory.views import (
    AdminAdvisoryListCreateAPIView,
    AdminAdvisoryUpdateDeleteAPIView,
    AdminAdvisoryFromDoctorAPIView,
    AdvisoryListAPIView,
    AdvisoryDetailAPIView,
)

urlpatterns = [
    # Admin endpoints (requires IsAdminUser)
    path("admin/advisory/", AdminAdvisoryListCreateAPIView.as_view(), name="admin-advisory-list-create"),
    path("admin/advisory/from-doctor/", AdminAdvisoryFromDoctorAPIView.as_view(), name="admin-advisory-from-doctor"),
    path("admin/advisory/<uuid:member_id>/", AdminAdvisoryUpdateDeleteAPIView.as_view(), name="admin-advisory-update-delete"),

    # User endpoints (requires IsAuthenticated) - only active members
    path("advisory/", AdvisoryListAPIView.as_view(), name="advisory-list"),
    path("advisory/<uuid:member_id>/", AdvisoryDetailAPIView.as_view(), name="advisory-detail"),
]
