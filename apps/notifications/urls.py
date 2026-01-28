from django.urls import path
from apps.notifications.views import AdminNotificationSummary, MarkAllNotificationsRead, AdminNotificationList

urlpatterns = [
    path("admin/notifications/summary/", AdminNotificationSummary.as_view()),
    path("admin/notifications/mark-read/", MarkAllNotificationsRead.as_view()),
    path("admin/notifications/", AdminNotificationList.as_view()),
]
