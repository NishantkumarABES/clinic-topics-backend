from django.urls import path
from apps.topics.views import (
    CleanupUnwantedImages, TopicCategoryListView, TopicListView, TopicDetailView, ExtractArticleDataView
)

urlpatterns = [
    path("categories/", TopicCategoryListView.as_view(), name="topic-categories"),
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),
    path("admin/extract-article/", ExtractArticleDataView.as_view(), name="extract-article-data"),
    path("admin/cleanup-unwanted-images/", CleanupUnwantedImages.as_view(), name="cleanup-unwanted-images"),

]