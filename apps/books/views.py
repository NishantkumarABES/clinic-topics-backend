from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend


from apps.books.models import Book
from apps.books.serializers import (
    BookListSerializer, BookUploadSerializer, BookDetailSerializer, BookReviewSerializer
)
from apps.books.constants import Status
from core.permissions import IsDoctor, IsAdmin


class BookListCreateView(generics.ListCreateAPIView):
    pagination_class = PageNumberPagination
    parser_classes = [MultiPartParser, FormParser]
    queryset = Book.objects.filter(status__in=[Status.APPROVED, Status.PENDING])
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]

    search_fields = ["title", "authors", "specialty", "isbn"]
    filterset_fields = ["specialty", "book_type", "publication_year", "status"]
    ordering_fields = ["created_at", "rating", "publication_year"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookUploadSerializer
        return BookListSerializer

    def perform_create(self, serializer):
        serializer.save()


class BookDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        book = get_object_or_404(Book, pk=pk, status=Status.APPROVED)
        book.views = models.F("views") + 1
        book.save(update_fields=["views"])

        book.refresh_from_db()
        serializer = BookDetailSerializer(book)
        return Response(serializer.data)


class BookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk, status=Status.APPROVED)
        book.downloads = models.F("downloads") + 1
        book.save(update_fields=["downloads"])
        return Response({"detail": "Download recorded"})



class PendingBookListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = BookListSerializer
    queryset = Book.objects.filter(status=Status.PENDING)


class BookReviewView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        book = get_object_or_404(Book, pk=pk, status=Status.PENDING)
        serializer = BookReviewSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Book review updated successfully"})
