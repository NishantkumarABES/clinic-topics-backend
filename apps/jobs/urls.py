from django.urls import path
from apps.jobs.views import (
    JobPostCreateView, MyJobPostListView, PublicJobPostListView, JobPostDetailView,
)

urlpatterns = [
    path("", PublicJobPostListView.as_view()),
    path("create/", JobPostCreateView.as_view()),
    path("me/", MyJobPostListView.as_view()),
    path("<uuid:pk>/", JobPostDetailView.as_view()),
]