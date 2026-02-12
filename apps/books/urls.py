from django.urls import path
from apps.books.views import (
    BookListView, BookDetailView, BookDownloadView, AdminBookListView, BookListView, BookReviewView, MyBooksView, BookUploadView,
    CreateBookPurchaseView, VerifyBookPurchaseView, MyBookDetailView, MoveBookToReviewView, MyBookUpdateView, BookRatingView,
    MyBookDeleteView
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
    path("<uuid:pk>/rate/", BookRatingView.as_view()),


    # -------------------------
    # Doctor APIs
    # -------------------------
    path("my/", MyBooksView.as_view(), name="my-books"),
    path("my/<uuid:pk>/", MyBookDetailView.as_view(), name="my-book-detail"),
    path("my/<uuid:pk>/update/", MyBookUpdateView.as_view(), name="my-book-update"),
    path("upload/", BookUploadView.as_view(), name="book-upload"),
    path("my/<uuid:pk>/delete/", MyBookDeleteView.as_view(), name="my-book-delete"),

    # -------------------------
    # Admin APIs
    # -------------------------
    path("admin/", AdminBookListView.as_view(), name="all-books"),
    path("admin/<uuid:pk>/review/", BookReviewView.as_view(), name="book-review"),
    path("admin/<uuid:pk>/move/", MoveBookToReviewView.as_view(), name="book-move"),
]