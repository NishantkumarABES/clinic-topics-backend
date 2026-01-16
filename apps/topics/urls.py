from django.urls import path
from apps.topics.views import (
    CleanupUnwantedImages, TopicListView, TopicDetailView, ExtractArticleDataView, AdminTopicListCreateAPIView, AdminTopicUpdateAPIView,
    AdminTopicUpdatePublishStatusAPIView, DoctorTopicCreateAPIView, TopicsFeedView
)

urlpatterns = [
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),

    path("admin/extract-article/", ExtractArticleDataView.as_view(), name="extract-article-data"),
    path("admin/cleanup-unwanted-images/", CleanupUnwantedImages.as_view(), name="cleanup-unwanted-images"),
    path("admin/topics/", AdminTopicListCreateAPIView.as_view(), name="admin-topic-list-create"),
    path("admin/topics/<uuid:topic_id>/", AdminTopicUpdateAPIView.as_view(), name="admin-topic-update"),
    path("admin/topics/<uuid:topic_id>/publish-status/", AdminTopicUpdatePublishStatusAPIView.as_view(), name="admin-topic-update-publish-status"),

    path("doctor/topics/create/", DoctorTopicCreateAPIView.as_view()),
    path("feed/", TopicsFeedView.as_view(), name="topics-feed"),
]