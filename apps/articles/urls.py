from django.urls import path
from apps.articles.views import (
    ArticleListView, ArticleDetailView, ToggleBookmarkView, ArticleDownloadView
)

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-list"),
    path("<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("<slug:slug>/bookmark/", ToggleBookmarkView.as_view(), name="article-bookmark"),
    path("<slug:slug>/download/", ArticleDownloadView.as_view(), name="article-download"),
]