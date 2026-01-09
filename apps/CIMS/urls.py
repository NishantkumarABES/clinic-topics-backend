from django.urls import path
from apps.CIMS.views import AdminCIMSListCreateAPIView, AdminCIMSUpdateAPIView

urlpatterns = [
    path("admin/cims/", AdminCIMSListCreateAPIView.as_view()),
    path("admin/cims/<uuid:cims_id>/", AdminCIMSUpdateAPIView.as_view()),
]