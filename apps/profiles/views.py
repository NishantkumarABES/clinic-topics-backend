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

        # if not ctx["instance"]:
        #     return Response({"detail": "Profile not found"}, status=404)

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







# Doctor profile APIs view
# class DoctorProfileView(APIView):
#     permission_classes = [IsDoctor]
#     parser_classes = [MultiPartParser, FormParser]

#     @swagger_auto_schema(
#         responses={
#             200: openapi.Response(
#                 description="Doctor profile retrieved successfully",
#                 schema=DoctorProfileSerializer,
#             ),
#             404: openapi.Response(
#                 description="Profile not created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def get(self, request):
#         try:
#             profile = request.user.doctor_profile
#         except ObjectDoesNotExist:
#             return Response(
#                 {"detail": "Doctor profile not created", "success": False},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         serializer = DoctorProfileSerializer(profile)
#         data = serializer.data
#         data["success"] = True
#         return Response(data)

#     @swagger_auto_schema(
#         request_body=DoctorProfileSerializer,
#         responses={
#             201: openapi.Response(
#                 description="Doctor profile created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             400: openapi.Response(
#                 description="Bad request",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Terms not accepted",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def post(self, request):
#         if not request.user.terms_accepted:
#             return Response(
#                 {"detail": "Accept terms and conditions first", "success": False},
#                 status=403
#             )

#         if not request.user.is_profile_complete():
#             return Response(
#                 {
#                     "detail": "Complete user profile before creating doctor profile",
#                     "success": False
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if hasattr(request.user, "doctor_profile"):
#             return Response(
#                 {"detail": "Doctor profile already exists", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         serializer = DoctorProfileSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         profile = serializer.save(user=request.user)

#         activate_user_if_eligible(request.user)

#         return Response(
#             {
#                 "message": "Doctor profile created",
#                 "success": True
#             },
#             status=status.HTTP_201_CREATED
#         )

#     @swagger_auto_schema(
#         request_body=DoctorProfileSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Doctor profile updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             404: openapi.Response(
#                 description="Profile not created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         try:
#             profile = request.user.doctor_profile
#         except ObjectDoesNotExist:
#             return Response(
#                 {"detail": "Doctor profile not created", "success": False},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         serializer = DoctorProfileSerializer(
#             profile, data=request.data, partial=True
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         return Response({"message": "Doctor profile updated", "success": True})

# class DoctorSectionUpdateMixin:
#     section_name = None
#     serializer_class = None

#     def get_swagger_schema(self):
#         return swagger_auto_schema(
#             request_body=self.serializer_class,
#             responses={
#                 200: openapi.Response(
#                     description="Section updated",
#                     schema=openapi.Schema(
#                         type=openapi.TYPE_OBJECT,
#                         properties={
#                             "message": openapi.Schema(type=openapi.TYPE_STRING),
#                         },
#                     ),
#                 ),
#                 403: openapi.Response(
#                     description="Section locked by admin",
#                     schema=openapi.Schema(
#                         type=openapi.TYPE_OBJECT,
#                         properties={
#                             "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                         },
#                     ),
#                 ),
#             },
#         )

#     def patch(self, request):
#         profile = request.user.doctor_profile

#         if profile.is_section_locked(self.section_name):
#             return Response(
#                 {"detail": "This section is locked by admin", "success": False},
#                 status=403
#             )

#         serializer = self.serializer_class(
#             profile, data=request.data, partial=True
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         update_doctor_section_completion(profile, self.section_name)

#         return Response({"message": f"{self.section_name} updated", "success": True})

# class DoctorOverviewUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "overview"
#     serializer_class = DoctorOverviewSerializer

#     @swagger_auto_schema(
#         request_body=DoctorOverviewSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class DoctorProfessionalUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "professional"
#     serializer_class = DoctorProfessionalSerializer

#     @swagger_auto_schema(
#         request_body=DoctorProfessionalSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class DoctorLicenseUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "license"
#     serializer_class = DoctorLicenseSerializer

#     @swagger_auto_schema(
#         request_body=DoctorLicenseSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class DoctorPracticeUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "practice"
#     serializer_class = DoctorPracticeSerializer

#     @swagger_auto_schema(
#         request_body=DoctorPracticeSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class DoctorAvailabilityUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "availability"
#     serializer_class = DoctorAvailabilitySerializer

#     @swagger_auto_schema(
#         request_body=DoctorAvailabilitySerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class DoctorAboutUpdateView(APIView, DoctorSectionUpdateMixin):
#     permission_classes = [IsDoctor]
#     section_name = "about"
#     serializer_class = DoctorAboutSerializer

#     @swagger_auto_schema(
#         request_body=DoctorAboutSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Section locked by admin",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)
    
# class DoctorLicenseUploadView(APIView):
#     permission_classes = [IsDoctor]
#     parser_classes = [MultiPartParser, FormParser]

#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter(
#                 name="license_document",
#                 in_=openapi.IN_FORM,
#                 type=openapi.TYPE_FILE,
#                 description="Doctor license document",
#                 required=True
#             )
#         ],
#         responses={
#             200: openapi.Response(
#                 description="License uploaded",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             400: openapi.Response(
#                 description="No document provided",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         profile = request.user.doctor_profile

#         if "license_document" not in request.FILES:
#             return Response(
#                 {"detail": "No document provided", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         profile.license_document = request.FILES["license_document"]
#         profile.save(update_fields=["license_document"])

#         return Response({"message": "License uploaded", "success": True})



# # Patient profile APIs view
# class PatientProfileView(APIView):
#     permission_classes = [IsAuthenticated, IsPatient]

#     @swagger_auto_schema(
#         responses={
#             200: openapi.Response(
#                 description="Patient profile retrieved successfully",
#                 schema=PatientProfileSerializer,
#             ),
#             404: openapi.Response(
#                 description="Profile not created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def get(self, request):
#         try:
#             profile = request.user.patient_profile
#         except ObjectDoesNotExist:
#             return Response(
#                 {"detail": "Patient profile not created", "success": False},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         serializer = PatientProfileSerializer(profile)
#         data = serializer.data
#         data["success"] = True
#         return Response(data)

#     @swagger_auto_schema(
#         request_body=PatientProfileSerializer,
#         responses={
#             201: openapi.Response(
#                 description="Patient profile created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                         "state": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             400: openapi.Response(
#                 description="Bad request",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             403: openapi.Response(
#                 description="Terms not accepted",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def post(self, request):
#         if not request.user.terms_accepted:
#             return Response(
#                 {"detail": "Accept terms and conditions first", "success": False},
#                 status=403
#             )

#         if not request.user.is_profile_complete():
#             return Response(
#                 {
#                     "detail": "Complete user profile before creating patient profile",
#                     "success": False
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if hasattr(request.user, "patient_profile"):
#             return Response(
#                 {"detail": "Patient profile already exists", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         serializer = PatientProfileSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         profile = serializer.save(user=request.user)

#         # Attempt lifecycle activation
#         activate_user_if_eligible(request.user)

#         return Response(
#             {
#                 "message": "Patient profile created",
#                 "state": request.user.state,
#                 "success": True
#             },
#             status=status.HTTP_201_CREATED
#         )

#     @swagger_auto_schema(
#         request_body=PatientProfileSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Patient profile updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             404: openapi.Response(
#                 description="Profile not created",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "detail": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         try:
#             profile = request.user.patient_profile
#         except ObjectDoesNotExist:
#             return Response(
#                 {"detail": "Patient profile not created", "success": False},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         serializer = PatientProfileSerializer(
#             profile,
#             data=request.data,
#             partial=True
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         return Response({"message": "Patient profile updated", "success": True})

# class PatientSectionUpdateMixin:
#     section_name = None
#     serializer_class = None

#     def get_swagger_schema(self):
#         return swagger_auto_schema(
#             request_body=self.serializer_class,
#             responses={
#                 200: openapi.Response(
#                     description="Section updated",
#                     schema=openapi.Schema(
#                         type=openapi.TYPE_OBJECT,
#                         properties={
#                             "message": openapi.Schema(type=openapi.TYPE_STRING),
#                         },
#                     ),
#                 ),
#             },
#         )

#     def patch(self, request):
#         profile = request.user.patient_profile

#         serializer = self.serializer_class(
#             profile, data=request.data, partial=True
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         update_patient_section_completion(profile, self.section_name)

#         return Response({"message": f"{self.section_name} updated", "success": True})

# class PatientMedicalUpdateView(APIView, PatientSectionUpdateMixin):
#     permission_classes = [IsPatient]
#     section_name = "medical"
#     serializer_class = PatientMedicalSerializer

#     @swagger_auto_schema(
#         request_body=PatientMedicalSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class PatientPersonalUpdateView(APIView, PatientSectionUpdateMixin):
#     permission_classes = [IsPatient]
#     section_name = "personal"
#     serializer_class = PatientPersonalSerializer

#     @swagger_auto_schema(
#         request_body=PatientPersonalSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class PatientEmergencyUpdateView(APIView, PatientSectionUpdateMixin):
#     permission_classes = [IsPatient]
#     section_name = "emergency"
#     serializer_class = PatientEmergencySerializer

#     @swagger_auto_schema(
#         request_body=PatientEmergencySerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)

# class PatientInsuranceUpdateView(APIView, PatientSectionUpdateMixin):
#     permission_classes = [IsPatient]
#     section_name = "insurance"
#     serializer_class = PatientInsuranceSerializer

#     @swagger_auto_schema(
#         request_body=PatientInsuranceSerializer,
#         responses={
#             200: openapi.Response(
#                 description="Section updated",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def patch(self, request):
#         return super().patch(request)
    

# # ADMIN APIs view
# class AdminDoctorListView(APIView):
#     permission_classes = [IsAuthenticated, IsAdmin]

#     @swagger_auto_schema(
#         responses={
#             200: openapi.Response(
#                 description="List of pending doctor profiles",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_ARRAY,
#                     items=openapi.Schema(
#                         type=openapi.TYPE_OBJECT,
#                         properties={
#                             "user_id": openapi.Schema(type=openapi.TYPE_STRING),
#                             "email": openapi.Schema(type=openapi.TYPE_STRING),
#                             "full_name": openapi.Schema(type=openapi.TYPE_STRING),
#                             "license_uploaded": openapi.Schema(type=openapi.TYPE_BOOLEAN),
#                             "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
#                         },
#                     ),
#                 ),
#             ),
#         },
#     )
#     def get(self, request):
#         profiles = DoctorProfile.objects.select_related("user")

#         data = []
#         for p in profiles:
#             data.append({
#                 "user_id": str(p.user.id),
#                 "email": p.user.email,
#                 "full_name": p.user.full_name,
#                 "license_uploaded": bool(p.license_document),
#                 "created_at": p.created_at,
#             })

#         return Response({"data": data, "success": True})

# class AdminDoctorSectionLockView(APIView):
#     permission_classes = [IsAdmin]

#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 "section": openapi.Schema(type=openapi.TYPE_STRING, description="Section name to lock"),
#             },
#             required=["section"],
#         ),
#         responses={
#             200: openapi.Response(
#                 description="Section locked",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#         },
#     )
#     def post(self, request, user_id):
#         section = request.data.get("section")

#         profile = DoctorProfile.objects.get(user_id=user_id)
#         if section not in profile.locked_sections:
#             profile.locked_sections.append(section)
#             profile.save(update_fields=["locked_sections"])

#         return Response({"message": f"{section} locked", "success": True})
