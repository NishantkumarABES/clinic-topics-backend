from django.urls import path
from apps.CIMS.views import (
    AdminCIMSListCreateAPIView,
    AdminCIMSUpdateAPIView,
    CIMSListAPIView,
    CIMSDetailAPIView,
)

urlpatterns = [
    # Admin endpoints (requires IsAdminUser)
    path("admin/cims/", AdminCIMSListCreateAPIView.as_view()),
    path("admin/cims/<uuid:cims_id>/", AdminCIMSUpdateAPIView.as_view()),

    # User endpoints (requires IsAuthenticated) - only published drugs
    path("cims/", CIMSListAPIView.as_view(), name="cims-list"),
    path("cims/<uuid:cims_id>/", CIMSDetailAPIView.as_view(), name="cims-detail"),
]