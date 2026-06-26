from django.urls import path
from apps.topics.views import (
    CleanupUnwantedImages, TopicListView, TopicDetailView, ExtractArticleDataView, AdminTopicListCreateAPIView, AdminTopicUpdateAPIView,
    AdminTopicUpdatePublishStatusAPIView, DoctorTopicCreateAPIView, TopicsFeedView, AdminTopicDetailView,
    StartTranscriptionAPIView, TranscriptionStatusAPIView, DownloadTranscriptAPIView, DownloadTranscriptSRTAPIView,
    TopicLikeToggleAPIView, TopicCommentCreateAPIView, RefineTitleView, TopicImageProxyView
)

urlpatterns = [
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),

    path("admin/extract-article/", ExtractArticleDataView.as_view(), name="extract-article-data"),
    path("admin/refine-title/", RefineTitleView.as_view(), name="refine-title"),
    path("admin/cleanup-unwanted-images/", CleanupUnwantedImages.as_view(), name="cleanup-unwanted-images"),
    path("admin/image-proxy/", TopicImageProxyView.as_view(), name="topic-image-proxy"),
    path("admin/topics/", AdminTopicListCreateAPIView.as_view(), name="admin-topic-list-create"),
    path("admin/topics/<uuid:topic_id>/", AdminTopicDetailView.as_view(), name="admin-topic-detail"),
    path("admin/topics/<uuid:topic_id>/update/", AdminTopicUpdateAPIView.as_view(), name="admin-topic-update"),
    path("admin/topics/<uuid:topic_id>/publish-status/", AdminTopicUpdatePublishStatusAPIView.as_view(), name="admin-topic-update-publish-status"),
    
    # Transcription endpoints
    path("admin/topics/<uuid:topic_id>/start-transcription/", StartTranscriptionAPIView.as_view(), name="start-transcription"),
    path("admin/topics/<uuid:topic_id>/transcription-status/", TranscriptionStatusAPIView.as_view(), name="transcription-status"),
    path("admin/topics/<uuid:topic_id>/transcript/", DownloadTranscriptAPIView.as_view(), name="download-transcript"),
    path("admin/topics/<uuid:topic_id>/transcript/srt/", DownloadTranscriptSRTAPIView.as_view(), name="download-transcript-srt"),

    path("doctor/topics/create/", DoctorTopicCreateAPIView.as_view()),
    path("feed/", TopicsFeedView.as_view(), name="topics-feed"),
    path("feed/<uuid:topic_id>/like/", TopicLikeToggleAPIView.as_view()),
    path("feed/<uuid:topic_id>/comment/", TopicCommentCreateAPIView.as_view()),
]
