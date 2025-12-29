from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.profiles.models import DoctorProfile
from apps.profiles.serializers import (
    DoctorProfileSerializer, PatientProfileSerializer, DoctorOverviewSerializer, DoctorProfessionalSerializer, DoctorLicenseSerializer, 
    DoctorPracticeSerializer, DoctorAvailabilitySerializer, DoctorAboutSerializer, PatientMedicalSerializer, PatientProfileSerializer, 
    PatientEmergencySerializer, PatientInsuranceSerializer, PatientPersonalSerializer
)
from core.permissions import IsDoctor, IsPatient, IsAdmin
from apps.accounts.services import activate_user_if_eligible
from apps.accounts.constants import UserState
from apps.profiles.services import update_doctor_section_completion, update_patient_section_completion


# Doctor profile APIs view
class DoctorProfileView(APIView):
    permission_classes = [IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Doctor profile retrieved successfully",
                schema=DoctorProfileSerializer,
            ),
            404: openapi.Response(
                description="Profile not created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        try:
            profile = request.user.doctor_profile
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Doctor profile not created", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorProfileSerializer(profile)
        data = serializer.data
        data["success"] = True
        return Response(data)

    @swagger_auto_schema(
        request_body=DoctorProfileSerializer,
        responses={
            201: openapi.Response(
                description="Doctor profile created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "verification_status": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Terms not accepted",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        if not request.user.terms_accepted:
            return Response(
                {"detail": "Accept terms and conditions first", "success": False},
                status=403
            )

        if not request.user.is_profile_complete():
            return Response(
                {
                    "detail": "Complete user profile before creating doctor profile",
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(request.user, "doctor_profile"):
            return Response(
                {"detail": "Doctor profile already exists", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = serializer.save(user=request.user)

        activate_user_if_eligible(request.user)

        return Response(
            {
                "message": "Doctor profile created",
                "verification_status": profile.verification_status,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        request_body=DoctorProfileSerializer,
        responses={
            200: openapi.Response(
                description="Doctor profile updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="Profile not created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        try:
            profile = request.user.doctor_profile
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Doctor profile not created", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorProfileSerializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Doctor profile updated", "success": True})

class DoctorSectionUpdateMixin:
    section_name = None
    serializer_class = None

    def get_swagger_schema(self):
        return swagger_auto_schema(
            request_body=self.serializer_class,
            responses={
                200: openapi.Response(
                    description="Section updated",
                    schema=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "message": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
                403: openapi.Response(
                    description="Section locked by admin",
                    schema=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
            },
        )

    def patch(self, request):
        profile = request.user.doctor_profile

        if profile.is_section_locked(self.section_name):
            return Response(
                {"detail": "This section is locked by admin", "success": False},
                status=403
            )

        serializer = self.serializer_class(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        update_doctor_section_completion(profile, self.section_name)

        return Response({"message": f"{self.section_name} updated", "success": True})

class DoctorOverviewUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "overview"
    serializer_class = DoctorOverviewSerializer

    @swagger_auto_schema(
        request_body=DoctorOverviewSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class DoctorProfessionalUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "professional"
    serializer_class = DoctorProfessionalSerializer

    @swagger_auto_schema(
        request_body=DoctorProfessionalSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class DoctorLicenseUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "license"
    serializer_class = DoctorLicenseSerializer

    @swagger_auto_schema(
        request_body=DoctorLicenseSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class DoctorPracticeUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "practice"
    serializer_class = DoctorPracticeSerializer

    @swagger_auto_schema(
        request_body=DoctorPracticeSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class DoctorAvailabilityUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "availability"
    serializer_class = DoctorAvailabilitySerializer

    @swagger_auto_schema(
        request_body=DoctorAvailabilitySerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class DoctorAboutUpdateView(APIView, DoctorSectionUpdateMixin):
    permission_classes = [IsDoctor]
    section_name = "about"
    serializer_class = DoctorAboutSerializer

    @swagger_auto_schema(
        request_body=DoctorAboutSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Section locked by admin",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)
    
class DoctorLicenseUploadView(APIView):
    permission_classes = [IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="license_document",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Doctor license document",
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="License uploaded",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="No document provided",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        profile = request.user.doctor_profile

        if "license_document" not in request.FILES:
            return Response(
                {"detail": "No document provided", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.license_document = request.FILES["license_document"]
        profile.save(update_fields=["license_document"])

        return Response({"message": "License uploaded", "success": True})

class DoctorVerificationStatusView(APIView):
    permission_classes = [IsDoctor]
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Verification status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "verification_status": openapi.Schema(type=openapi.TYPE_STRING),
                        "user_state": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="Profile not created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        try:
            profile = request.user.doctor_profile
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Doctor profile not created", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "verification_status": profile.verification_status,
            "user_state": request.user.state,
            "success": True
        })


# Patient profile APIs view
class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Patient profile retrieved successfully",
                schema=PatientProfileSerializer,
            ),
            404: openapi.Response(
                description="Profile not created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        try:
            profile = request.user.patient_profile
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Patient profile not created", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PatientProfileSerializer(profile)
        data = serializer.data
        data["success"] = True
        return Response(data)

    @swagger_auto_schema(
        request_body=PatientProfileSerializer,
        responses={
            201: openapi.Response(
                description="Patient profile created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "state": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            403: openapi.Response(
                description="Terms not accepted",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        if not request.user.terms_accepted:
            return Response(
                {"detail": "Accept terms and conditions first", "success": False},
                status=403
            )

        if not request.user.is_profile_complete():
            return Response(
                {
                    "detail": "Complete user profile before creating patient profile",
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(request.user, "patient_profile"):
            return Response(
                {"detail": "Patient profile already exists", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = serializer.save(user=request.user)

        # Attempt lifecycle activation
        activate_user_if_eligible(request.user)

        return Response(
            {
                "message": "Patient profile created",
                "state": request.user.state,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        request_body=PatientProfileSerializer,
        responses={
            200: openapi.Response(
                description="Patient profile updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="Profile not created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        try:
            profile = request.user.patient_profile
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Patient profile not created", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PatientProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Patient profile updated", "success": True})

class PatientSectionUpdateMixin:
    section_name = None
    serializer_class = None

    def get_swagger_schema(self):
        return swagger_auto_schema(
            request_body=self.serializer_class,
            responses={
                200: openapi.Response(
                    description="Section updated",
                    schema=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "message": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
            },
        )

    def patch(self, request):
        profile = request.user.patient_profile

        serializer = self.serializer_class(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        update_patient_section_completion(profile, self.section_name)

        return Response({"message": f"{self.section_name} updated", "success": True})

class PatientMedicalUpdateView(APIView, PatientSectionUpdateMixin):
    permission_classes = [IsPatient]
    section_name = "medical"
    serializer_class = PatientMedicalSerializer

    @swagger_auto_schema(
        request_body=PatientMedicalSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class PatientPersonalUpdateView(APIView, PatientSectionUpdateMixin):
    permission_classes = [IsPatient]
    section_name = "personal"
    serializer_class = PatientPersonalSerializer

    @swagger_auto_schema(
        request_body=PatientPersonalSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class PatientEmergencyUpdateView(APIView, PatientSectionUpdateMixin):
    permission_classes = [IsPatient]
    section_name = "emergency"
    serializer_class = PatientEmergencySerializer

    @swagger_auto_schema(
        request_body=PatientEmergencySerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)

class PatientInsuranceUpdateView(APIView, PatientSectionUpdateMixin):
    permission_classes = [IsPatient]
    section_name = "insurance"
    serializer_class = PatientInsuranceSerializer

    @swagger_auto_schema(
        request_body=PatientInsuranceSerializer,
        responses={
            200: openapi.Response(
                description="Section updated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def patch(self, request):
        return super().patch(request)
    

# ADMIN APIs view
class AdminDoctorPendingListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="List of pending doctor profiles",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "user_id": openapi.Schema(type=openapi.TYPE_STRING),
                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                            "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "license_uploaded": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        },
                    ),
                ),
            ),
        },
    )
    def get(self, request):
        profiles = DoctorProfile.objects.filter(
            verification_status="pending"
        ).select_related("user")

        data = []
        for p in profiles:
            data.append({
                "user_id": str(p.user.id),
                "email": p.user.email,
                "full_name": p.user.full_name,
                "license_uploaded": bool(p.license_document),
                "created_at": p.created_at,
            })

        return Response({"data": data, "success": True})

class AdminDoctorApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Doctor approved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="License document not uploaded",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="Doctor profile not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def post(self, request, user_id):
        try:
            profile = DoctorProfile.objects.select_related("user").get(
                user_id=user_id
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"detail": "Doctor profile not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        if not profile.license_document:
            return Response(
                {"detail": "License document not uploaded", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.verification_status = "approved"
        profile.save(update_fields=["verification_status"])

        user = profile.user
        user.state = UserState.ACTIVE
        user.save(update_fields=["state"])

        return Response({"message": "Doctor approved", "success": True})

class AdminDoctorRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Doctor rejected",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="Doctor profile not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def post(self, request, user_id):
        try:
            profile = DoctorProfile.objects.select_related("user").get(
                user_id=user_id
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"detail": "Doctor profile not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        profile.verification_status = "rejected"
        profile.save(update_fields=["verification_status"])

        user = profile.user
        user.state = UserState.REJECTED
        user.save(update_fields=["state"])

        return Response({"message": "Doctor rejected", "success": True})

class AdminDoctorSectionLockView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "section": openapi.Schema(type=openapi.TYPE_STRING, description="Section name to lock"),
            },
            required=["section"],
        ),
        responses={
            200: openapi.Response(
                description="Section locked",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    def post(self, request, user_id):
        section = request.data.get("section")

        profile = DoctorProfile.objects.get(user_id=user_id)
        if section not in profile.locked_sections:
            profile.locked_sections.append(section)
            profile.save(update_fields=["locked_sections"])

        return Response({"message": f"{section} locked", "success": True})