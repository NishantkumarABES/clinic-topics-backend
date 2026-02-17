from django.urls import path
from apps.jobs.views import (
    JobListView, JobDetailView, JobApplyView, MyJobsView, MyJobDetailView,
    MyJobCreateView, MyJobUpdateView, MyJobDeleteView, MyAppliedJobsView, MyAppliedJobDetailView,
    AdminApplicationListView, AdminJobCreateView, AdminJobUpdateView, MoveJobToReviewView, 
    AdminJobReviewView, CloseJobView, MyJobApplicationsView, ReviewApplicationView,
    MyJobApplicationsDetailView, AdminJobListView
)

urlpatterns = [
    # Public
    path("", JobListView.as_view(), name="job-list"),
    path("<uuid:pk>/", JobDetailView.as_view(), name="job-detail"),

    # Doctor
    path("my-jobs/", MyJobsView.as_view(), name="my-jobs"),
    path("my-jobs/<uuid:pk>/", MyJobDetailView.as_view(), name="my-job-detail"),
    path("<uuid:pk>/apply/", JobApplyView.as_view(), name="job-apply"),
    path("my-applied-jobs/", MyAppliedJobsView.as_view(), name="my-applied-jobs"),
    path("my-applied-jobs/<uuid:pk>/", MyAppliedJobDetailView.as_view(), name="my-applied-job-detail"),
    path("create/", MyJobCreateView.as_view(), name="job-create"),
    path("<uuid:pk>/update/", MyJobUpdateView.as_view(), name="job-update"),
    path("<uuid:pk>/delete/", MyJobDeleteView.as_view(), name="job-delete"),
    path("<uuid:pk>/applications/", MyJobApplicationsView.as_view(), name="doctor-application-list"),
    path(
        "<uuid:job_id>/applications/<uuid:application_id>/",
        MyJobApplicationsDetailView.as_view(),
        name="doctor-application-detail",
    ),
    path(
        "<uuid:job_id>/applications/<uuid:application_id>/review/",
         ReviewApplicationView.as_view(), 
         name="doctor-application-review"
    ),
    path("<uuid:pk>/close/", CloseJobView.as_view(), name="close-job"),

    # Admin 
    path("admin/create/", AdminJobCreateView.as_view(), name="admin-job-create"),
    path("admin/jobs/", AdminJobListView.as_view(), name="admin-job-list"),
    path("admin/jobs/<uuid:pk>/update/", AdminJobUpdateView.as_view(), name="admin-job-update"),
    path("admin/jobs/<uuid:pk>/review/", AdminJobReviewView.as_view(), name="admin-job-review"),
    path("admin/jobs/<uuid:pk>/move/", MoveJobToReviewView.as_view(), name="move-job-to-review"),
    path("admin/jobs/<uuid:pk>/applications/", AdminApplicationListView.as_view(), name="admin-application-list"),
]