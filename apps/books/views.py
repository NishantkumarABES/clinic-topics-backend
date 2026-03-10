from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.core.files.storage import default_storage
from django.db.models import Q, Count


from apps.books.models import Book, BookPurchase, BookCategory
from apps.books.serializers import (
    BookListSerializer, BookUploadSerializer, BookDetailSerializer, BookReviewSerializer, PaginatedBookListResponseSerializer,
    CreateBookPurchaseSerializer, VerifyBookPurchaseSerializer, StandardResponseSerializer, BookDownloadResponseSerializer,
    BookUpdateSerializer, BookRatingSerializer, BookRatingListSerializer, AdminBookCreateSerializer, BookCategorySerializer,
    AdminBookPurchaseSerializer
)
from apps.books.constants import Status, OrderStatus
from core.permissions import IsDoctor, IsAdmin
from core.api_responses import BAD_REQUEST_400, UNAUTHORIZE_401
from external.razorpay.service import razorpay_service


class BooksLandingView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="search",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Search in category label or key (partial match)"
            ),
        ]
    )
    def get(self, request):
        search = request.query_params.get("search")

        book_counts = (
            Book.objects
            .filter(status=Status.APPROVED, is_deleted=False)
            .exclude(speciality__isnull=True)
            .values("speciality")
            .annotate(count=Count("id"))
        )

        book_count_map = {
            item["speciality"]: item["count"]
            for item in book_counts
        }

        categories = BookCategory.objects.filter(is_active=True)
        if search:
            categories = categories.filter(
                models.Q(label__icontains=search) |
                models.Q(key__icontains=search) 
            )

        response_data = []

        for category in categories:
            image_url = None
            if category.image:
                image_url = request.build_absolute_uri(category.image.url)

            response_data.append({
                "key": category.key,
                "label": category.label,
                "image": image_url,
                "book_count": book_count_map.get(category.key, 0)
            })

        return Response({
            "detail": "Book categories retrieved successfully",
            "data": {"categories": response_data},
            "success": True
        })

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
                name="speciality",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by speciality"
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
        queryset = Book.objects.filter(
            status=Status.APPROVED, is_deleted=False
        )

        search = request.query_params.get("search")
        speciality = request.query_params.get("speciality")
        book_type = request.query_params.get("book_type")
        ordering = request.query_params.get("ordering", "-created_at")

        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(authors__icontains=search) |
                models.Q(isbn__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

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
            Book, id=pk,
            status=Status.APPROVED,
            is_deleted=False
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
                "razorpay_order_id": "",
                "order_status": OrderStatus.PENDING_PAYMENT
            }
        )

        if purchase.is_paid:
            return Response(
                {"detail": "Book already purchased", "success": True}
            )

        order = razorpay_service.create_order(
            amount=book.price * 100,
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
        razorpay_payment_id = data["razorpay_payment_id"]
        purchase.razorpay_payment_id = razorpay_payment_id
        purchase.razorpay_signature = data["razorpay_signature"]
        payment_details = razorpay_service.fetch_payment(razorpay_payment_id)
        purchase.payment_method = payment_details.get("method", "unknown")
        purchase.is_paid = True
        purchase.order_status = OrderStatus.PAID
        purchase.save(update_fields=[
            "razorpay_payment_id", "is_paid", "payment_method", "razorpay_signature", "order_status"
        ])

        return Response(
            {
                "detail": "Payment successful", 
                "data": {
                    "order_id": data["razorpay_order_id"],
                    "payment_id": data["razorpay_payment_id"],
                    "status": OrderStatus.PAID
                },
                "success": True
            }
        )

class BookRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=BookRatingSerializer,
        responses={200: StandardResponseSerializer},
        operation_description="Rate a book from 1–5 with optional comment."
    )
    def post(self, request, pk):

        book = get_object_or_404(
            Book, id=pk,
            status=Status.APPROVED,
            is_deleted=False
        )

        serializer = BookRatingSerializer(
            data=request.data,
            context={
                "request": request,
                "book": book
            }
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Rating submitted successfully",
            "success": True,
        })

class BookRatingListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BookPagination

    @swagger_auto_schema(
        responses={200: StandardResponseSerializer},
        operation_description="Get all ratings for a particular book (paginated)."
    )
    def get(self, request, pk):

        book = get_object_or_404(
            Book,
            id=pk,
            status=Status.APPROVED,
            is_deleted=False
        )

        queryset = book.ratings.select_related("user").order_by("-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BookRatingListSerializer(page, many=True)
        paginated_response = paginator.get_paginated_response(serializer.data)
        return Response(
            {
                "detail": "Book ratings fetched successfully",
                "data": paginated_response.data,
                "success": True,
            }
        )

class BookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={200: BookDownloadResponseSerializer},
        operation_description="Generate a secure download URL and record the download."
    )
    def post(self, request, pk):

        # Fetch without filtering first — we must inspect deletion state
        book = get_object_or_404(Book, id=pk)

        # -------------------------------------------------
        # DELETION ACCESS CONTROL
        # -------------------------------------------------
        if book.is_deleted:
            has_access = BookPurchase.objects.filter(
                user=request.user,
                book=book,
                is_paid=True
            ).exists()

            if not has_access:
                return Response(
                    {
                        "detail": "This book is no longer available.",
                        "success": False
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        # -------------------------------------------------
        # APPROVAL GUARD
        # Prevent downloading pending/rejected books
        # BUT allow purchasers if it was deleted AFTER purchase
        # -------------------------------------------------
        if book.status != Status.APPROVED and not book.is_deleted:
            return Response(
                {
                    "detail": "Book is not available for download.",
                    "success": False
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # -------------------------------------------------
        # PAYMENT ACCESS CONTROL
        # -------------------------------------------------
        if book.price > 0:
            has_access = BookPurchase.objects.filter(
                user=request.user,
                book=book,
                is_paid=True
            ).exists()

            if not has_access:
                return Response(
                    {
                        "detail": "Purchase required",
                        "success": False
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # -------------------------------------------------
        # ATOMIC DOWNLOAD UPDATE
        # -------------------------------------------------
        with transaction.atomic():

            Book.objects.filter(pk=book.pk).update(
                downloads=models.F("downloads") + 1
            )

            public_id = book.file.name
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
                name="speciality",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by speciality"
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
        queryset = Book.objects.filter(
            uploaded_by=request.user, is_deleted=False
        )
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        speciality = request.query_params.get("speciality")
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
        if speciality:
            queryset = queryset.filter(speciality=speciality)
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

class MyBookDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={
            200: BookDetailSerializer,
        },
    )
    def get(self, request, pk):
        book = get_object_or_404(
            Book, id=pk, uploaded_by=request.user
        )

        serializer = BookDetailSerializer(
            book, context={"request": request}
        )

        return Response({
            "detail": "Book details fetched",
            "data": serializer.data,
            "success": True,
        })

class MyBookDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    @swagger_auto_schema(
        responses={200: BookDownloadResponseSerializer},
        operation_description="Generate a secure download URL for the doctor's own book."
    )
    def post(self, request, pk):
        book = get_object_or_404(
            Book, id=pk,
            uploaded_by=request.user
        )
        public_id = book.file.name
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

class MyBookUpdateView(APIView):
    """
    Doctor can update their uploaded book ONLY while it is pending.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=BookUpdateSerializer,
        responses={200: StandardResponseSerializer},
        operation_description="Update uploaded book (allowed only when status is pending)."
    )
    def patch(self, request, pk):

        book = get_object_or_404(
            Book, id=pk,
            uploaded_by=request.user
        )

        # 🔐 Guard condition
        if book.status == Status.INREVIEW:
            return Response(
                {
                    "detail": "Book cannot be edited once it enters review state.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if book.is_deleted:
            return Response(
                {
                    "detail": "Deleted books cannot be edited.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookUpdateSerializer(
            book, data=request.data,
            partial=True
        )

        
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Book updated successfully.",
                "data": None,
                "success": True,
            }
        )

class MyBookDeleteView(APIView):
    """
    Soft delete a book.
    Purchasers retain access.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={200: StandardResponseSerializer},
        operation_description="Soft delete a book. Purchased users retain access."
    )
    def delete(self, request, pk):

        book = get_object_or_404(
            Book,
            id=pk,
            uploaded_by=request.user
        )

        if book.is_deleted:
            return Response(
                {"detail": "Book already deleted.", "success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        book.is_deleted = True
        book.save(update_fields=["is_deleted"])

        return Response({
            "detail": "Book deleted successfully.",
            "success": True,
        })

# -------------------------
# Admin APIs
# -------------------------

class AdminBookListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = BookPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        queryset = Book.objects.select_related("uploaded_by").all()

        # ---- Filters ----
        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        book_type = request.GET.get("book_type")
        status = request.GET.get("status")
        ordering = request.GET.get("ordering")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(authors__icontains=search) |
                Q(publisher__icontains=search) |
                Q(isbn__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality__iexact=speciality)

        if book_type:
            queryset = queryset.filter(book_type=book_type)

        if status:
            queryset = queryset.filter(status=status)

        if ordering:
            queryset = queryset.order_by(ordering)

        # ---- Pagination ----
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = BookListSerializer(page, many=True, context={"request": request})
        paginated_response = paginator.get_paginated_response(serializer.data)
        paginated_response.data["detail"] = "All books fetched"
        paginated_response.data["success"] = True

        return paginated_response

class BookReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        request_body=BookReviewSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
        auto_schema=None
    )
    def patch(self, request, pk):
        book = get_object_or_404(
            Book,
            id=pk,
            status__in=[Status.PENDING, Status.INREVIEW]
        )

        serializer = BookReviewSerializer(
            book, data=request.data, partial=True
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Book review updated successfully",
                "data": None,
                "success": True,
            }
        )

class MoveBookToReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={200: StandardResponseSerializer},
        operation_description="Move book from pending to in_review.",
        auto_schema=None
    )
    def patch(self, request, pk):

        book = get_object_or_404(
            Book, id=pk, status=Status.PENDING
        )

        book.status = Status.INREVIEW
        book.save(update_fields=["status"])

        return Response(
            {
                "detail": "Book moved to in-review.",
                "success": True,
            }
        )

class AdminBookUpdateView(APIView):
    """
    Admin can update ANY book metadata.
    Unlike doctors, admin is NOT restricted by book status.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=BookUpdateSerializer,
        responses={200: StandardResponseSerializer},
        operation_description="Admin update book details.",
        auto_schema=None
    )
    def patch(self, request, pk):

        book = get_object_or_404(Book, id=pk)
        if book.is_deleted:
            return Response(
                {
                    "detail": "Deleted books cannot be edited.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BookUpdateSerializer(
            book, data=request.data,
            partial=True
        )

        
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Book updated successfully by admin.",
                "data": serializer.data,
                "success": True,
            }
        )

class AdminBookCreateView(APIView):
    """
    Admin can create a book on behalf of a doctor.
    Book is auto-approved.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=AdminBookCreateSerializer,
        responses={201: StandardResponseSerializer},
        operation_description="Admin creates a book for a doctor (auto approved).",
        auto_schema=None
    )
    def post(self, request):

        serializer = AdminBookCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        book = serializer.save()

        return Response(
            {
                "detail": "Book created and approved successfully.",
                "data": {"book_id": str(book.id)},
                "success": True,
            },
            status=status.HTTP_201_CREATED,
        )

class AdminBookCategoryCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=BookCategorySerializer,
        responses={201: StandardResponseSerializer},
        operation_description="Create a book category with image",
        auto_schema=None
    )
    def post(self, request):

        serializer = BookCategorySerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response(
            {
                "detail": "Book category created successfully",
                "data": {
                    "category_id": category.id
                },
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class AdminBookPurchaseListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    pagination_class = BookPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):

        queryset = (
            BookPurchase.objects
            .select_related("user", "book")
            .order_by("-created_at")
        )

        # -------- Filters --------
        search = request.GET.get("search")
        status_filter = request.GET.get("status")
        payment_method = request.GET.get("payment_method")

        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(book__title__icontains=search) |
                Q(razorpay_payment_id__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(order_status=status_filter)
            
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
            
        # -------- Pagination --------
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = AdminBookPurchaseSerializer(page, many=True)

        paginated_response = paginator.get_paginated_response(serializer.data)

        return Response({
            "detail": "Book purchases fetched successfully",
            "data": paginated_response.data,
            "success": True
        })