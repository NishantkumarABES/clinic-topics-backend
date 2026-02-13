from django.urls import path
from apps.analytics.views.dashboard import (
    AdminDashboardMetricsAPIView, AdminDashboardPendingActionAPIView, OrderStatusAnalyticsAPIView, TopSellingProductsAPIView,
    RevenueAnalyticsAPIView
)
from apps.analytics.views.patient import PatientAnalyticsAPIView
from apps.analytics.views.doctor import DoctorAnalyticsView
from apps.analytics.views.products import ProductAnalyticsView
from apps.analytics.views.topics import TopicsAnalyticsView
from apps.analytics.views.events import EventsAnalyticsView
from apps.analytics.views.advisory import AdvisoryAnalyticsView

from apps.analytics.views.my_reposit.books import BooksAnalyticsView
from apps.analytics.views.my_reposit.articles import ArticlesAnalyticsView



urlpatterns = [
    path("admin/dashboard/metrics/", AdminDashboardMetricsAPIView.as_view()),
    path("admin/dashboard/pending-actions/", AdminDashboardPendingActionAPIView.as_view()),
    path("admin/dashboard/top-selling-products/", TopSellingProductsAPIView.as_view()),
    path("admin/dashboard/revenue-analytics/", RevenueAnalyticsAPIView.as_view()),
    path("admin/dashboard/order-status-analytics/", OrderStatusAnalyticsAPIView.as_view()),

    path("admin/patients/metrics/", PatientAnalyticsAPIView.as_view()),
    path("admin/doctors/metrics/", DoctorAnalyticsView.as_view()),
    path("admin/products/metrics/", ProductAnalyticsView.as_view()),
    path("admin/topics/metrics/", TopicsAnalyticsView.as_view()),
    path("admin/events/metrics/", EventsAnalyticsView.as_view()),
    path("admin/advisory/metrics/", AdvisoryAnalyticsView.as_view()),

    path("admin/books/metrics/", BooksAnalyticsView.as_view()),
    path("admin/articles/metrics/", ArticlesAnalyticsView.as_view()),
]