from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.profiles.models import DoctorProfile
from apps.advisory.models import AdvisoryMember
from apps.advisory.serializers import (
    AdvisoryMemberReadSerializer, AdvisoryMemberWriteSerializer, AdvisoryPagination, StandardResponseSerializer,
    AdvisoryMemberDetailResponseSerializer, AdvisoryMemberListResponseSerializer, AdvisoryMemberCreateUpdateResponseSerializer, 
    DoctorToAdvisoryRequestSerializer
)
from core.api_responses import BAD_REQUEST_400, UNAUTHORIZE_401, NOT_FOUND_404


# ============================================
# ADMIN ENDPOINTS
# ============================================

class AdminAdvisoryListCreateAPIView(APIView):
    """Admin endpoint to list and create advisory members."""
    permission_classes = [IsAdminUser]
    pagination_class = AdvisoryPagination
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="List all advisory members (admin only) with optional search and status filters",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search by name, email, phone, or specialization"),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by status (active/inactive)"),
        ],
        auto_schema=None,
        responses={
            200: AdvisoryMemberListResponseSerializer,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")

        queryset = AdvisoryMember.objects.all()

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(specialization__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = AdvisoryMemberReadSerializer(page, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        
        return Response({
            "detail": "Advisory members retrieved successfully",
            "data": paginated_data,
            "success": True
        })

    @swagger_auto_schema(
        operation_description="Create a new advisory member (admin only)",
        request_body=AdvisoryMemberWriteSerializer,
        responses={
            201: AdvisoryMemberCreateUpdateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
        auto_schema=None,
    )
    def post(self, request):
        serializer = AdvisoryMemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        return Response(
            {
                "detail": "Advisory member created successfully",
                "data": AdvisoryMemberReadSerializer(member).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class AdminAdvisoryFromDoctorAPIView(APIView):
    """Admin endpoint to create advisory member from existing doctor."""
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Create advisory member from existing doctor profile (admin only)",
        request_body=DoctorToAdvisoryRequestSerializer,
        auto_schema=None,
        responses={
            201: AdvisoryMemberCreateUpdateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def post(self, request):
        doctor_id = request.data.get("doctor_id")
        if not doctor_id:
            return Response(
                {"detail": "doctor_id is required", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            doctor = DoctorProfile.objects.select_related("user").get(user_id=doctor_id)
        except DoctorProfile.DoesNotExist:
            return Response(
                {"detail": "Doctor not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if advisory member with this email already exists
        if AdvisoryMember.objects.filter(email=doctor.user.email).exists():
            return Response(
                {"detail": "This doctor is already an advisory member", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create advisory member from doctor data
        member = AdvisoryMember.objects.create(
            full_name=doctor.user.full_name,
            email=doctor.user.email,
            phone=doctor.user.phone or "",
            gender=doctor.user.gender,
            date_of_birth=doctor.user.date_of_birth,
            specialization=doctor.specialization or "",
            years_of_experience=doctor.years_of_experience or 0,
            bio=doctor.bio or "",
            image=doctor.profile_photo if doctor.profile_photo else None,
            status="active"
        )
        
        return Response(
            {
                "detail": "Doctor added to advisory panel successfully",
                "data": AdvisoryMemberReadSerializer(member).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class AdminAdvisoryUpdateDeleteAPIView(APIView):
    """Admin endpoint to update or delete advisory members."""
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Update an advisory member (admin only)",
        request_body=AdvisoryMemberWriteSerializer,
        auto_schema=None,
        responses={
            200: AdvisoryMemberCreateUpdateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def patch(self, request, member_id):
        member = get_object_or_404(AdvisoryMember, id=member_id)

        serializer = AdvisoryMemberWriteSerializer(
            member,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        return Response(
            {
                "detail": "Advisory member updated successfully",
                "data": AdvisoryMemberReadSerializer(member).data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        operation_description="Delete an advisory member (admin only)",
        responses={
            200: StandardResponseSerializer,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
        auto_schema=None,
    )
    def delete(self, request, member_id):
        member = get_object_or_404(AdvisoryMember, id=member_id)
        member.delete()

        return Response(
            {
                "detail": "Advisory member deleted successfully",
                "data": None,
                "success": True
            },
            status=status.HTTP_200_OK
        )

# ============================================
# USER ENDPOINTS (Authenticated Users)
# ============================================

class AdvisoryListAPIView(APIView):
    """List all active advisory members for authenticated users."""
    permission_classes = [IsAuthenticated]
    pagination_class = AdvisoryPagination

    @swagger_auto_schema(
        operation_description="List all active advisory members",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Search by name or specialization"),
        ],
        responses={
            200: AdvisoryMemberListResponseSerializer,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request):
        search = request.query_params.get("search")

        # Only return active members for regular users
        queryset = AdvisoryMember.objects.filter(status="active")

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(specialization__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = AdvisoryMemberReadSerializer(page, many=True)
        paginated_data = paginator.get_paginated_response(serializer.data).data
        
        return Response(
            {
                "detail": "Advisory members retrieved successfully",
                "data": paginated_data,
                "success": True,
            },
            status=status.HTTP_200_OK
        )

class AdvisoryDetailAPIView(APIView):
    """Get a single active advisory member for authenticated users."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get details of a single active advisory member",
        responses={
            200: AdvisoryMemberDetailResponseSerializer,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def get(self, request, member_id):
        # Only allow access to active members
        member = get_object_or_404(AdvisoryMember, id=member_id, status="active")

        serializer = AdvisoryMemberReadSerializer(member)
        return Response(
            {
                "detail": "Advisory member retrieved successfully",
                "data": serializer.data,
                "success": True
            },
            status=status.HTTP_200_OK
        )
