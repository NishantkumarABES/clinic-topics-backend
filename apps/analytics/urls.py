from django.urls import path
from apps.analytics.views.dashboard import AdminDashboardMetricsAPIView
from apps.analytics.views.patient import PatientAnalyticsAPIView

urlpatterns = [
    path("admin/dashboard/metrics/", AdminDashboardMetricsAPIView.as_view()),
    path("admin/patients/analytics/", PatientAnalyticsAPIView.as_view()),
]