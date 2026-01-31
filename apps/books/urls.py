from django.urls import path
from apps.books.views import (
    BookListCreateView, BookDetailView, BookDownloadView, PendingBookListView, BookReviewView
)

urlpatterns = [
    path("", BookListCreateView.as_view(), name="book-list-create"),
    path("<uuid:pk>/", BookDetailView.as_view(), name="book-detail"),
    path("<uuid:pk>/download/", BookDownloadView.as_view(), name="book-download"),

    path("reviews/pending/", PendingBookListView.as_view(), name="books-pending"),
    path("<uuid:pk>/review/", BookReviewView.as_view(), name="book-review"),
]
