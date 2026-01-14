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






