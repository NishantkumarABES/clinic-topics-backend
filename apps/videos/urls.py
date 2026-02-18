from django.urls import path
from apps.videos.views import (
    VideoDetailView, VideoListView, VideoDownloadView, MyVideoDetailView, MyVideoListView, MyVideoDownloadView,
    VideoCreateView, VideoUpdateView, SoftDeleteVideoView, AdminVideoCreateView, AdminVideoUpdateView,
    AdminVideoListView, AdminMoveToReviewView, VideoReviewView
)



urlpatterns = [
    path("", VideoListView.as_view(), name="video-list"),
    path("<uuid:id>/", VideoDetailView.as_view(), name="video-detail"),
    path("<uuid:id>/download/", VideoDownloadView.as_view(), name="video-download"),

    path("my/", MyVideoListView.as_view(), name="my-video-list"),
    path("my/<uuid:id>/", MyVideoDetailView.as_view(), name="my-video-detail"),
    path("my/<uuid:id>/download/", MyVideoDownloadView.as_view(), name="my-video-download"),
    path("create/", VideoCreateView.as_view(), name="video-create"),
    path("<uuid:id>/update/", VideoUpdateView.as_view(), name="video-update"),
    path("<uuid:id>/delete/", SoftDeleteVideoView.as_view(), name="video-delete"),

    path("admin/", AdminVideoListView.as_view(), name="admin-video-list"),
    path("admin/create/", AdminVideoCreateView.as_view(), name="admin-video-create"),
    path("admin/update/<uuid:id>/", AdminVideoUpdateView.as_view(), name="admin-video-update"),
    path("admin/move/<uuid:id>/", AdminMoveToReviewView.as_view(), name="admin-move-to-review"),
    path("admin/review/<uuid:id>/", VideoReviewView.as_view(), name="admin-video-review"),
]