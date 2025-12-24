from django.urls import path
from apps.topics.views import TopicCategoryListView, TopicListView, TopicDetailView

urlpatterns = [
    path("categories/", TopicCategoryListView.as_view(), name="topic-categories"),
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),
]