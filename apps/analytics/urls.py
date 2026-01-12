from django.urls import path
from apps.analytics.views.dashboard import AdminDashboardMetricsAPIView
from apps.analytics.views.patient import PatientAnalyticsAPIView
from apps.analytics.views.doctor import DoctorAnalyticsView
from apps.analytics.views.products import ProductAnalyticsView
from apps.analytics.views.topics import TopicsAnalyticsView
from apps.analytics.views.events import EventsAnalyticsView





urlpatterns = [
    path("admin/dashboard/metrics/", AdminDashboardMetricsAPIView.as_view()),
    path("admin/patients/metrics/", PatientAnalyticsAPIView.as_view()),
    path("admin/doctors/metrics/", DoctorAnalyticsView.as_view()),
    path("admin/products/metrics/", ProductAnalyticsView.as_view()),
    path("admin/topics/metrics/", TopicsAnalyticsView.as_view()),
    path("admin/events/metrics/", EventsAnalyticsView.as_view()),
]