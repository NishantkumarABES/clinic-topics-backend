from django.urls import path
from apps.articles.views import (
    ArticleListView, ArticleDetailView, ToggleBookmarkView, ArticleCreateView, MyArticlesView, 
    ArticleUpdateView, ArticleReviewView, AdminMoveToReviewView, AdminArticleListView,
    BookmarkListView, SoftDeleteArticleView
)

urlpatterns = [
    # public
    path("", ArticleListView.as_view(), name="article-list"),
    path("<uuid:id>/", ArticleDetailView.as_view(), name="article-detail"),
    path("<uuid:id>/bookmark/", ToggleBookmarkView.as_view(), name="article-bookmark"),
    path("create/", ArticleCreateView.as_view(), name="article-create"),

    # Doctors
    path("my/", MyArticlesView.as_view(), name="my-articles"),
    path("<uuid:id>/update/", ArticleUpdateView.as_view(), name="article-update"),
    path("<uuid:id>/delete/", SoftDeleteArticleView.as_view(), name="article-delete"),
    path("bookmarks/", BookmarkListView.as_view(), name="bookmark-list"),

    # Admin
    path("admin/", AdminArticleListView.as_view(), name="admin-article-list"),
    path("admin/<uuid:id>/review/", ArticleReviewView.as_view(), name="article-review"),
    path("admin/<uuid:id>/admin-move-review/", AdminMoveToReviewView.as_view(), name="admin-move-review"),
]
