from django.urls import path
from apps.events.views import EventListView, EventDetailView, EventRegisterView


urlpatterns = [
    path("", EventListView.as_view(), name="event-list"),
    path("<int:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("<int:event_id>/register/", EventRegisterView.as_view(), name="event-register"),
]