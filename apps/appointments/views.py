from django.db.models import Q, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.accounts.constants import UserRole
from apps.profiles.models import DoctorProfile
from apps.appointments.serializers import (
    DoctorListSerializer, DoctorDetailSerializer,
    DoctorListResponseSerializer, DoctorDetailResponseSerializer
)
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401


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

        queryset = DoctorProfile.objects.select_related("user").all()

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
            "data": {"doctors": serializer.data},
            "success": True,
            "count": paginated_response.data.get("count"),
            "next": paginated_response.data.get("next"),
            "previous": paginated_response.data.get("previous"),
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

        serializer = DoctorDetailSerializer(doctor_profile)

        return Response({
            "detail": "Doctor details retrieved successfully",
            "data": {"doctor": serializer.data},
            "success": True
        })
