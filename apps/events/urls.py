from django.urls import path
from apps.events.views import EventListCreateAPIView, EventRetrieveUpdateAPIView

urlpatterns = [
    path("", EventListCreateAPIView.as_view()),
    path("<uuid:id>/", EventRetrieveUpdateAPIView.as_view()),
]