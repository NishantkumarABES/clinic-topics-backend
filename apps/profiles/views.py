from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.profiles.models import DoctorProfile, PatientProfile
from apps.profiles.serializers import DoctorProfileSerializer, PatientProfileSerializer
from apps.accounts.constants import UserRole




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
        responses={
            200: openapi.Response(
                description="User profile",
                schema=DoctorProfileSerializer  # documented representative schema
            ),
        },
    )
    def get(self, request):
        ctx = self.get_profile_context(request)

        if not ctx:
            return Response({"detail": "Unsupported role"}, status=400)

        if not ctx["instance"]:
            user = request.user

            return Response({
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "country_code": user.country_code,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                **ctx["serializer"](ctx["instance"]).data
            })

        return Response(ctx["serializer"](ctx["instance"]).data)

    @swagger_auto_schema(
        request_body=PatientProfileSerializer,
        responses={
            201: openapi.Response(
                description="Profile created",
                schema=PatientProfileSerializer,
            ),
        },
    )
    def post(self, request):
        ctx = self.get_profile_context(request)

        if not ctx or not ctx["allow_post"]:
            return Response(
                {"detail": "POST not allowed for this user"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        if ctx["instance"]:
            return Response(
                {"detail": "Profile already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ctx["serializer"](data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=PatientProfileSerializer,
        responses={
            201: openapi.Response(
                description="Profile created",
                schema=PatientProfileSerializer,
            ),
        },
    )
    def patch(self, request):
        ctx = self.get_profile_context(request)

        if not ctx:
            return Response({"detail": "Unsupported role"}, status=400)

        if not ctx["instance"]:
            return Response({"detail": "Profile not found"}, status=404)

        serializer = ctx["serializer"](
            ctx["instance"],
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)




class DoctorRatingView(APIView):
    """
    View and submit ratings for doctors.
    GET: List ratings for a doctor (public)
    POST: Submit a rating (patient only)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Doctor ratings",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ratings": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        "average_rating": openapi.Schema(type=openapi.TYPE_NUMBER),
                        "total_ratings": openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
        },
    )
    def get(self, request, doctor_id):
        """Get ratings for a specific doctor."""
        from apps.profiles.models import DoctorRating
        from apps.profiles.serializers import DoctorRatingSerializer
        from apps.accounts.models import User
        from django.db.models import Avg, Count

        try:
            doctor = User.objects.get(id=doctor_id, role="doctor")
        except User.DoesNotExist:
            return Response(
                {"detail": "Doctor not found", "success": False},
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
            "doctor_id": str(doctor_id),
            "doctor_name": doctor.full_name,
            "ratings": serializer.data,
            "average_rating": round(aggregates["average_rating"] or 0, 1),
            "total_ratings": aggregates["total_ratings"],
            "rating_breakdown": breakdown,
            "success": True
        })

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["second_opinion_doctor_request_id", "rating"],
            properties={
                "second_opinion_doctor_request_id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                "rating": openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                "review": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: openapi.Response(description="Rating created"),
            400: openapi.Response(description="Validation error"),
        },
    )
    def post(self, request, doctor_id):
        """Submit a rating for a doctor after completed second opinion."""
        from apps.profiles.serializers import DoctorRatingCreateSerializer
        from apps.accounts.constants import UserRole

        # Verify user is a patient
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can submit ratings", "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DoctorRatingCreateSerializer(
            data=request.data,
            context={"request": request, "doctor_id": doctor_id}
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save()

        return Response({
            "detail": "Rating submitted successfully",
            "rating_id": str(rating.id),
            "success": True
        }, status=status.HTTP_201_CREATED)


