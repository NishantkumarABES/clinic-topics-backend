from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.core.files.storage import default_storage

from apps.books.models import Book, BookPurchase
from apps.books.serializers import (
    BookListSerializer, BookUploadSerializer, BookDetailSerializer, BookReviewSerializer, PaginatedBookListResponseSerializer,
    CreateBookPurchaseSerializer, VerifyBookPurchaseSerializer, StandardResponseSerializer, BookDownloadResponseSerializer
)
from apps.books.constants import Status
from core.permissions import IsDoctor, IsAdmin
from core.api_responses import BAD_REQUEST_400, UNAUTHORIZE_401
from external.razorpay.service import razorpay_service


# -------------------------
# Pagination (Accounts-style)
# -------------------------
class BookPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

# -------------------------
# Public APIs
# -------------------------
class BookListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BookPagination

    @swagger_auto_schema(
        responses={
            200: PaginatedBookListResponseSerializer,
        },
        operation_description="Retrieve a paginated list of approved books. Supports search, filtering and sorting.",
        manual_parameters=[
            openapi.Parameter(
                name="search",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Search in title, authors or ISBN (partial match)"
            ),
            openapi.Parameter(
                name="specialty",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by specialty"
            ),
            openapi.Parameter(
                name="book_type",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by book type"
            ),
            openapi.Parameter(
                name="ordering",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description='Ordering field(s), e.g. "-created_at", "title", etc. Default: "-created_at"',
                default="-created_at"
            ),
        ],
    )
    def get(self, request):
        queryset = Book.objects.filter(status=Status.APPROVED)

        search = request.query_params.get("search")
        specialty = request.query_params.get("specialty")
        book_type = request.query_params.get("book_type")
        ordering = request.query_params.get("ordering", "-created_at")

        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(authors__icontains=search) |
                models.Q(isbn__icontains=search)
            )

        if specialty:
            queryset = queryset.filter(specialty=specialty)

        if book_type:
            queryset = queryset.filter(book_type=book_type)

        queryset = queryset.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = BookListSerializer(page, many=True)

        response = paginator.get_paginated_response(serializer.data).data

        return Response({
            "detail": "Books fetched successfully",
            "data": response, "success": True
        })

class BookDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: BookDetailSerializer,
        },
    )
    def get(self, request, pk):
        book = get_object_or_404(
            Book, id=pk, status=Status.APPROVED
        )

        book.views = models.F("views") + 1
        book.save(update_fields=["views"])
        book.refresh_from_db()

        serializer = BookDetailSerializer(
            book, context={"request": request}
        )

        return Response({
            "detail": "Book details fetched",
            "data": serializer.data,
            "success": True,
        })

class CreateBookPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=CreateBookPurchaseSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        serializer = CreateBookPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book = get_object_or_404(
            Book,
            id=serializer.validated_data["book_id"],
            status=Status.APPROVED
        )

        if book.price == 0:
            return Response(
                {"detail": "This book is free", "success": False},
                status=400
            )

        purchase, created = BookPurchase.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={
                "amount": book.price,
                "currency": "INR",
                "razorpay_order_id": ""
            }
        )

        if purchase.is_paid:
            return Response(
                {"detail": "Book already purchased", "success": True}
            )

        order = razorpay_service.create_order(
            amount=book.price,
            receipt=str(purchase.id),
            notes={"book_id": str(book.id), "user_id": str(request.user.id)}
        )

        purchase.razorpay_order_id = order["id"]
        purchase.save(update_fields=["razorpay_order_id"])

        return Response(
            {
                "detail": "Order created",
                "data": {
                    "order_id": order["id"],
                    "amount": order["amount"],
                    "currency": order["currency"],
                },
                "success": True,
            }
        )

class VerifyBookPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=VerifyBookPurchaseSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        serializer = VerifyBookPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        purchase = get_object_or_404(
            BookPurchase,
            razorpay_order_id=data["razorpay_order_id"],
            user=request.user
        )

        is_valid = razorpay_service.verify_payment_signature(
            data["razorpay_order_id"],
            data["razorpay_payment_id"],
            data["razorpay_signature"]
        )

        if not is_valid:
            return Response(
                {"detail": "Payment verification failed", "success": False},
                status=400
            )

        purchase.razorpay_payment_id = data["razorpay_payment_id"]
        purchase.is_paid = True
        purchase.save(update_fields=["razorpay_payment_id", "is_paid"])

        return Response(
            {"detail": "Payment successful", "success": True}
        )


# -------------------------
# Doctor Users APIs
# -------------------------
class BookUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=BookUploadSerializer,
        responses={
            201: BookDetailSerializer,
        },
    )
    def post(self, request):
        serializer = BookUploadSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False}
            )

        serializer.save(
            uploaded_by=request.user,
            status=Status.PENDING
        )

        return Response(
            {
                "detail": "Book submitted for review",
                "data": None,
                "success": True,
            },
            status=status.HTTP_201_CREATED,
        )

class MyBooksView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    pagination_class = BookPagination

    @swagger_auto_schema(
        responses={
            200: PaginatedBookListResponseSerializer,
        },
        operation_description="Retrieve a paginated list of books uploaded by the doctor. Supports search, filtering and sorting.",
        manual_parameters=[
            openapi.Parameter(
                name="status",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by book status"
            ),
            openapi.Parameter(
                name="search",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Search in title, authors or ISBN (partial match)"
            ),
            openapi.Parameter(
                name="specialty",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by specialty"
            ),
            openapi.Parameter(
                name="book_type",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by book type"
            ),
            openapi.Parameter(
                name="ordering",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False, 
                description='Ordering field(s), e.g. "-created_at", "title", etc. Default: "-created_at"',
                default="-created_at"
            ),
        ],
    )
    def get(self, request):
        queryset = Book.objects.filter(uploaded_by=request.user)
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        specialty = request.query_params.get("specialty")
        book_type = request.query_params.get("book_type")
        ordering = request.query_params.get("ordering", "-created_at")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(authors__icontains=search) |
                models.Q(isbn__icontains=search)
            )
        if specialty:
            queryset = queryset.filter(specialty=specialty)
        if book_type:
            queryset = queryset.filter(book_type=book_type)
        queryset = queryset.order_by(ordering)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BookListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data).data
        return Response(
            {
                "detail": "My books fetched",
                "data": response, "success": True,
            }
        )

class BookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={200: BookDownloadResponseSerializer},
        operation_description="Generate a secure download URL and record the download."
    )
    def post(self, request, pk):
        book = get_object_or_404(
            Book, id=pk,
            status=Status.APPROVED
        )

        # --- Access Control ---
        if book.price > 0:
            has_access = BookPurchase.objects.filter(
                user=request.user,
                book=book,
                is_paid=True
            ).exists()

            if not has_access:
                return Response(
                    {"detail": "Purchase required", "success": False},
                    status=status.HTTP_403_FORBIDDEN
                )

        # --- Atomic update + URL generation ---
        with transaction.atomic():
            Book.objects.filter(pk=book.pk).update(
                downloads=models.F("downloads") + 1
            )

            public_id = book.file.name
            print("Public ID:", public_id)
            download_url = default_storage.url(public_id)

        serializer = BookDownloadResponseSerializer(
            {"download_url": download_url}
        )

        return Response(
            {
                "detail": "Download URL generated",
                "data": serializer.data,
                "success": True,
            }
        )


# -------------------------
# Admin APIs
# -------------------------
class PendingBookListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = BookPagination

    # @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        queryset = Book.objects.filter(status=Status.PENDING).order_by("-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = BookListSerializer(page, many=True)

        response = paginator.get_paginated_response(serializer.data).data
        response["detail"] = "Pending books fetched"
        response["success"] = True

        return Response(response)

class BookReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        request_body=BookReviewSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def patch(self, request, pk):
        book = get_object_or_404(
            Book, id=pk, status=Status.PENDING
        )

        serializer = BookReviewSerializer(
            book, data=request.data, partial=True
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False}
            )
        serializer.save()

        return Response(
            {
                "detail": "Book review updated successfully",
                "data": None,
                "success": True,
            }
        )

