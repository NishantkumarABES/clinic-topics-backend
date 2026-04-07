from django.db.models import Q, Avg, Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.constants import UserRole
from apps.appointments.models import AppointmentCategory
from apps.profiles.models import DoctorProfile
from apps.appointments.serializers import (
    DoctorListSerializer, DoctorDetailSerializer, AppointmentCategorySerializer,
    DoctorListResponseSerializer, DoctorDetailResponseSerializer
)
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401
from core.permissions import IsAdmin

class AppointmentLandingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Get doctor counts grouped by specialization
        doctor_counts = (
            DoctorProfile.objects
            .exclude(user__state="deleted")
            .values("specialization")
            .annotate(count=Count("id"))
        )

        # Convert to dictionary for quick lookup
        doctor_count_map = {
            item["specialization"]: item["count"]
            for item in doctor_counts
        }

        # Fetch ALL categories (even if zero doctors)
        categories = AppointmentCategory.objects.filter(is_active=True)

        response_data = []

        for category in categories:
            response_data.append({
                "key": category.key,
                "label": category.label,
                "image": category.image.url if category.image else None,
                "doctor_count": doctor_count_map.get(category.key, 0)
            })

        return Response({
            "detail": "Doctor categories retrieved successfully",
            "data": {
                "categories": response_data
            },
            "success": True
        })

class DoctorListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class DoctorListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = DoctorListPagination

    @swagger_auto_schema(
        operation_description="Get paginated list of doctors for patient appointments",
        manual_parameters=[
            openapi.Parameter(
                'specialization', openapi.IN_QUERY,
                description="Filter by specialization (case-insensitive)",
                type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                'min_experience', openapi.IN_QUERY,
                description="Minimum years of experience",
                type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                'max_fee', openapi.IN_QUERY,
                description="Maximum consultation fee",
                type=openapi.TYPE_NUMBER, required=False
            ),
            openapi.Parameter(
                'min_rating', openapi.IN_QUERY,
                description="Minimum average rating",
                type=openapi.TYPE_NUMBER, required=False
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY,
                description="Search by doctor name or clinic name",
                type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                'page', openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY,
                description="Number of items per page (max 50)",
                type=openapi.TYPE_INTEGER, required=False
            ),
        ],
        responses={
            200: DoctorListResponseSerializer,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
        },
    )
    def get(self, request):
        # Only patients allowed
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can view doctors", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        # queryset = DoctorProfile.objects.select_related("user").all()
        queryset = (
            DoctorProfile.objects
            .select_related("user")
            .exclude(user__state="deleted")
        )
        # ---------- Filters ----------
        specialization = request.query_params.get("specialization")
        min_experience = request.query_params.get("min_experience")
        max_fee = request.query_params.get("max_fee")
        min_rating = request.query_params.get("min_rating")
        search = request.query_params.get("search")

        if specialization:
            queryset = queryset.filter(
                specialization__icontains=specialization
            )

        if min_experience:
            queryset = queryset.filter(
                years_of_experience__gte=int(min_experience)
            )

        if max_fee:
            queryset = queryset.filter(
                consultation_fee__lte=max_fee
            )

        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search) |
                Q(clinic_name__icontains=search)
            )

        # Rating filter (requires annotation)
        if min_rating:
            queryset = queryset.annotate(
                avg_rating=Avg("user__ratings_received__rating")
            ).filter(avg_rating__gte=float(min_rating))

        queryset = queryset.order_by("-created_at")

        # ---------- Pagination ----------
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = DoctorListSerializer(page, many=True)

        # Build standardized paginated response
        paginated_response = paginator.get_paginated_response(serializer.data)
        return Response({
            "detail": "Doctors retrieved successfully",
            "data": paginated_response.data,
            "success": True,
        })

class DoctorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get detailed information about a specific doctor",
        responses={
            200: DoctorDetailResponseSerializer,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
            404: NOT_FOUND_404,
        },
    )
    def get(self, request, doctor_id):
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can view doctor details", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            doctor_profile = DoctorProfile.objects.select_related("user").get(
                user__id=doctor_id
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"detail": "Doctor not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorDetailSerializer(doctor_profile, context={"request": request})

        return Response({
            "detail": "Doctor details retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class AppointmentCategoryListCreateView(ListCreateAPIView):
    """
    Admin API:
    - GET: List all categories
    - POST: Create category
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = AppointmentCategory.objects.all()
    serializer_class = AppointmentCategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Optional filter
        is_active = request.query_params.get("is_active")
        search = request.query_params.get("search")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        
        if search:
            queryset = queryset.filter(
                Q(key__icontains=search) |
                Q(label__icontains=search)
            )

        # ---------- OPTIMIZED DOCTOR COUNT ----------
        doctor_counts = (
            DoctorProfile.objects
            .exclude(user__state="deleted")
            .values("specialization")
            .annotate(count=Count("id"))
        )

        doctor_count_map = {
            item["specialization"]: item["count"]
            for item in doctor_counts
        }
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        # Inject doctor_count (override serializer)
        for item in data:
            item["doctor_count"] = doctor_count_map.get(item["key"], 0)


        return Response({
            "detail": "Categories retrieved successfully",
            "data": {
                "categories": serializer.data
            },
            "success": True
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": "Category created successfully",
                "data": serializer.data,
                "success": True
            }, status=status.HTTP_201_CREATED)

        return Response({
            "detail": "Validation failed",
            "data": serializer.errors,
            "success": False
        }, status=status.HTTP_400_BAD_REQUEST)

class AppointmentCategoryDetailView(RetrieveUpdateDestroyAPIView):
    """
    Admin API:
    - GET: Retrieve single category
    - PATCH/PUT: Update category
    - DELETE: Delete category
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = AppointmentCategory.objects.all()
    serializer_class = AppointmentCategorySerializer
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            "detail": "Category retrieved successfully",
            "data": serializer.data,
            "success": True
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.get("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": "Category updated successfully",
                "data": serializer.data,
                "success": True
            })

        return Response({
            "detail": "Validation failed",
            "data": serializer.errors,
            "success": False
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()

        return Response({
            "detail": "Category deleted successfully",
            "data": None,
            "success": True
        }, status=status.HTTP_204_NO_CONTENT)
