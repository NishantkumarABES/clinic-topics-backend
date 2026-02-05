from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from apps.profiles.models import DoctorProfile, PatientProfile
from apps.profiles.serializers import (
    DoctorProfileSerializer, PatientProfileSerializer,
    StandardResponseSerializer, DoctorProfileResponseSerializer,
    PatientProfileResponseSerializer, RatingCreateResponseSerializer,
    RatingsListResponseSerializer, DoctorRatingSerializer,
    DoctorRatingCreateSerializer
)
from apps.accounts.constants import UserRole
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401


class ProfileMeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_profile_context(self, request):
        user = request.user

        if user.role == UserRole.DOCTOR:
            return {
                "model": DoctorProfile,
                "serializer": DoctorProfileSerializer,
                "instance": getattr(user, "doctor_profile", None),
                "allow_post": False,
            }

        if user.role == UserRole.PATIENT:
            return {
                "model": PatientProfile,
                "serializer": PatientProfileSerializer,
                "instance": getattr(user, "patient_profile", None),
                "allow_post": True,
            }

        return None

    @swagger_auto_schema(
        operation_description="Get current user's profile",
        responses={
            200: DoctorProfileResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request):
        ctx = self.get_profile_context(request)

        if not ctx:
            return Response(
                {"detail": "Unsupported role", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        serializer_data = ctx["serializer"](ctx["instance"]).data if ctx["instance"] else {}
        
        # Build profile data with user fields first, then overlay profile-specific fields
        profile_data = {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "country_code": user.country_code,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender,
        }
        
        # Add profile-specific fields (excluding user fields that are already set)
        for key, value in serializer_data.items():
            if key not in ["full_name", "email", "phone", "country_code", "date_of_birth", "gender"]:
                profile_data[key] = value
            elif key in ["date_of_birth", "gender"] and value:
                # Only override if serializer has a non-empty value
                profile_data[key] = value
        
        return Response({
            "detail": "Profile retrieved successfully",
            "data": profile_data,
            "success": True
        })

    @swagger_auto_schema(
        operation_description="Create patient profile",
        request_body=PatientProfileSerializer,
        responses={
            201: PatientProfileResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            405: StandardResponseSerializer,
        },
    )
    def post(self, request):
        ctx = self.get_profile_context(request)

        if not ctx or not ctx["allow_post"]:
            return Response(
                {"detail": "POST not allowed for this user", "data": None, "success": False},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        if ctx["instance"]:
            return Response(
                {"detail": "Profile already exists", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ctx["serializer"](data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(user=request.user)

        return Response({
            "detail": "Profile created successfully",
            "data": serializer.data,
            "success": True
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Update current user's profile",
        request_body=PatientProfileSerializer,
        responses={
            200: PatientProfileResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def patch(self, request):
        ctx = self.get_profile_context(request)

        if not ctx:
            return Response(
                {"detail": "Unsupported role", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not ctx["instance"]:
            return Response(
                {"detail": "Profile not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ctx["serializer"](
            ctx["instance"],
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()

        return Response({
            "detail": "Profile updated successfully",
            "data": serializer.data,
            "success": True
        })

class DoctorRatingView(APIView):
    """
    View and submit ratings for doctors.
    GET: List ratings for a doctor (public)
    POST: Submit a rating (patient only)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get ratings for a specific doctor",
        responses={
            200: RatingsListResponseSerializer,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def get(self, request, doctor_id):
        """Get ratings for a specific doctor."""
        from apps.profiles.models import DoctorRating
        from apps.accounts.models import User
        from django.db.models import Avg, Count

        try:
            doctor = User.objects.get(id=doctor_id, role="doctor")
        except User.DoesNotExist:
            return Response(
                {"detail": "Doctor not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        ratings = DoctorRating.objects.filter(doctor=doctor).order_by("-created_at")

        # Calculate aggregates
        aggregates = ratings.aggregate(
            average_rating=Avg("rating"),
            total_ratings=Count("id")
        )

        # Rating breakdown
        breakdown = {}
        for i in range(1, 6):
            breakdown[str(i)] = ratings.filter(rating=i).count()

        serializer = DoctorRatingSerializer(ratings[:20], many=True)  # Latest 20

        return Response({
            "detail": "Ratings retrieved successfully",
            "data": {
                "doctor_id": str(doctor_id),
                "doctor_name": doctor.full_name,
                "ratings": serializer.data,
                "average_rating": round(aggregates["average_rating"] or 0, 1),
                "total_ratings": aggregates["total_ratings"],
                "rating_breakdown": breakdown,
            },
            "success": True
        })

    @swagger_auto_schema(
        operation_description="Submit a rating for a doctor after completed second opinion",
        request_body=DoctorRatingCreateSerializer,
        responses={
            201: RatingCreateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            403: StandardResponseSerializer,
        },
    )
    def post(self, request, doctor_id):
        """Submit a rating for a doctor after completed second opinion."""
        from apps.accounts.constants import UserRole

        # Verify user is a patient
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can submit ratings", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorRatingCreateSerializer(
            data=request.data,
            context={"request": request, "doctor_id": doctor_id}
        )
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        rating = serializer.save()

        return Response({
            "detail": "Rating submitted successfully",
            "data": {"rating_id": str(rating.id)},
            "success": True
        }, status=status.HTTP_201_CREATED)
