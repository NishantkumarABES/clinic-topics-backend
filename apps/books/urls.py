from django.urls import path
from apps.books.views import (
    BookListView, BookDetailView, BookDownloadView, PendingBookListView, BookReviewView, MyBooksView, BookUploadView,
    CreateBookPurchaseView, VerifyBookPurchaseView, MyBookDetailView
)

urlpatterns = [
    # -------------------------
    # Public / Authenticated APIs
    # -------------------------
    path("", BookListView.as_view(), name="book-list"),
    path("<uuid:pk>/", BookDetailView.as_view(), name="book-detail"),
    path("<uuid:pk>/download/", BookDownloadView.as_view(), name="book-download"),
    path("purchase/create/", CreateBookPurchaseView.as_view()),
    path("purchase/verify/", VerifyBookPurchaseView.as_view()),


    # -------------------------
    # Doctor APIs
    # -------------------------
    path("my/", MyBooksView.as_view(), name="my-books"),
    path("my/<uuid:pk>/", MyBookDetailView.as_view(), name="my-book-detail"),
    path("upload/", BookUploadView.as_view(), name="book-upload"),


    # -------------------------
    # Admin APIs
    # -------------------------
    path("admin/pending/", PendingBookListView.as_view(), name="books-pending"),
    path("admin/<uuid:pk>/review/", BookReviewView.as_view(), name="book-review"),
]