from django.urls import path
from apps.notifications.views import (
    AdminNotificationSummary, MarkAllNotificationsRead, AdminNotificationList,
    UserNotificationListView, MarkNotificationReadView, MarkAllNotificationsReadView
)

urlpatterns = [
    path("admin/notifications/summary/", AdminNotificationSummary.as_view()),
    path("admin/notifications/mark-read/", MarkAllNotificationsRead.as_view()),
    path("admin/notifications/", AdminNotificationList.as_view()),

    path("user/notifications/", UserNotificationListView.as_view()),
    path("user/notifications/mark-read/", MarkNotificationReadView.as_view()),
    path("user/notifications/mark-all-read/", MarkAllNotificationsReadView.as_view()),
]
