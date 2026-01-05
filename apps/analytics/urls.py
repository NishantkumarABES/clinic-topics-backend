from django.urls import path
from apps.analytics.views.dashboard import AdminDashboardMetricsAPIView
from apps.analytics.views.patient import PatientAnalyticsAPIView
from apps.analytics.views.doctor import DoctorAnalyticsView


urlpatterns = [
    path("admin/dashboard/metrics/", AdminDashboardMetricsAPIView.as_view()),
    path("admin/patients/analytics/", PatientAnalyticsAPIView.as_view()),
    path("admin/doctors/analytics/", DoctorAnalyticsView.as_view()),
]