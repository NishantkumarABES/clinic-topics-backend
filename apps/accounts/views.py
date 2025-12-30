from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers import (
    EmailLoginSerializer, PhoneOTPRequestSerializer, PhoneOTPVerifySerializer, SocialLoginSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailOTPRequestSerializer, EmailOTPVerifySerializer, RegisterSerializer, UserMeSerializer,
    UserListSerializer
)
from apps.accounts.services import (
    activate_user_if_eligible, resolve_social_user, create_password_reset_token, send_email_otp, send_phone_otp,
    get_tokens_for_user, can_resend_otp, anonymize_user
)
from apps.accounts.social_providers import social_provider_verification
from apps.accounts.models import User
from apps.accounts.constants import UserState, UserRole
from core.permissions import IsAdmin




class EmailOTPRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailOTPRequestSerializer,
        responses={
            200: openapi.Response(
                    description="success",
                    schema=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "detail": openapi.Schema(type=openapi.TYPE_STRING),
                            "testing-otp": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
        },
    )
    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = send_email_otp(email)
        return Response({"detail": "OTP sent to email", "testing-otp": otp, "success": True})

class EmailOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailOTPVerifySerializer,
        responses={
            200: openapi.Response(
                description="Email verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Invalid OTP",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="User not found",
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
        serializer = EmailOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_valid = serializer.validated_data["is_valid"]
        otp_obj = serializer.validated_data["otp_obj"]
        message = serializer.validated_data.get("message", "")
        try:
            if not is_valid:
                return Response(
                    {"detail": message, "success": False},
                )
            otp_obj.mark_as_used()
            return Response({"detail": "Email verified successfully", "success": True})
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this email does not exist", "success": False},
                status=404
            )

class PhoneOTPRequestView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=PhoneOTPRequestSerializer,
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "testing-otp": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            429: openapi.Response(
                description="Too many requests",
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
        phone = request.data.get("phone")

        if not can_resend_otp(phone):
            return Response(
                {"detail": "Please wait before requesting another OTP", "success": False},
                status=429
            )
        
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        otp = send_phone_otp(phone)

        return Response({"detail": "OTP sent", "testing-otp": otp, "success": True})

class PhoneOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=PhoneOTPVerifySerializer,
        responses={
            200: openapi.Response(
                description="Phone verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Invalid OTP",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            404: openapi.Response(
                description="User not found",
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
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_valid = serializer.validated_data["is_valid"]
        otp_obj = serializer.validated_data["otp_obj"]
        
        try:
            if not is_valid:
                return Response(
                    {"detail": "Invalid OTP", "success": False},
                    status=400
                )
            otp_obj.mark_as_used()
            return Response({"detail": "Phone verified successfully", "success": True})
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this phone number does not exist", "success": False},
                status=404
            )

class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "role": openapi.Schema(type=openapi.TYPE_STRING),
                        "state": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: openapi.Response(description="Validation error"),
        },
    )
    def post(self, request, role):
        # ---- Normalize & validate role ----
        role = role.lower()

        if role not in dict(UserRole.CHOICES):
            return Response(
                {"detail": "Invalid role", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---- Inject role into request data ----
        data = request.data.copy()
        data["role"] = role

        serializer = RegisterSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        access_token, refresh_token = get_tokens_for_user(user, False)
        return Response(
            {
                "access": access_token,
                "refresh": refresh_token,
                "user": {
                    "id": str(user.id),
                    "role": user.role,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "date_of_birth": user.date_of_birth,
                    "gender": user.gender,
                    "state": user.state,
                    "is_email_verified": user.is_email_verified,
                    "is_phone_verified": user.is_phone_verified,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                },
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )


class EmailLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access token"),
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token"),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING),
                                "role": openapi.Schema(type=openapi.TYPE_STRING),
                                "state": openapi.Schema(type=openapi.TYPE_STRING),
                                "onboarding_complete": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user:
            return Response(
                {"error": serializer.validated_data.get("error"), "success": False}
            )

        remember_me = request.data.get("remember_me", False)
        access_token, refresh_token = get_tokens_for_user(user, remember_me)

        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": {
                "id": str(user.id),
                "role": user.role,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "state": user.state,
                "is_email_verified": user.is_email_verified,
                "is_phone_verified": user.is_phone_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            },
            "success": True
        })

class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=SocialLoginSerializer,
        responses={
            200: openapi.Response(
                description="Social login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access token"),
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token"),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING),
                                "role": openapi.Schema(type=openapi.TYPE_STRING),
                                "state": openapi.Schema(type=openapi.TYPE_STRING),
                                "onboarding_complete": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    },
                ),
            ),
        },
    )

    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        token = serializer.validated_data["token"]
        role = serializer.validated_data.get("role")

        verifier = social_provider_verification.get(provider)

        if not verifier:
            raise AuthenticationFailed("Unsupported provider")

        social_user = verifier(token)

        user, created = resolve_social_user(social_user, role)
        activate_user_if_eligible(user)

        remember_me = request.data.get("remember_me", False)
        access_token, refresh_token = get_tokens_for_user(user, remember_me)

        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": {
                "id": str(user.id),
                "role": user.role,
                "state": user.state,
                "user": {
                    "id": str(user.id),
                    "role": user.role,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "date_of_birth": user.date_of_birth,
                    "gender": user.gender,
                    "state": user.state,
                    "is_email_verified": user.is_email_verified,
                    "is_phone_verified": user.is_phone_verified,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
            },
            "success": True
        })

class PhoneLoginView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=PhoneOTPVerifySerializer,
        responses={
            200: openapi.Response(
                description="Phone login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access token"), 
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token"),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING),
                                "role": openapi.Schema(type=openapi.TYPE_STRING),
                                "state": openapi.Schema(type=openapi.TYPE_STRING),
                                "onboarding_complete": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_valid = serializer.validated_data["is_valid"]
        otp_obj = serializer.validated_data["otp_obj"]
        phone = serializer.validated_data["phone"]

        if not is_valid:
            return Response(
                {"detail": serializer.validated_data.get("message", "Invalid OTP"), "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone=phone)
            if not user.is_phone_verified:
                return Response(
                    {"detail": "Phone number not verified", "success": False},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this phone number does not exist", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_obj.mark_as_used()
        access_token, refresh_token = get_tokens_for_user(user)

        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": {
                "id": str(user.id),
                "role": user.role,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "state": user.state,
                "is_email_verified": user.is_email_verified,
                "is_phone_verified": user.is_phone_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            },
            "success": True
        })
                    


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    @swagger_auto_schema(
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                description="Password reset email sent",
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
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            reset_token = create_password_reset_token(user)

            # Stub email sender (replace later)
            print(
                f"[RESET PASSWORD] http://frontend/reset-password?token={reset_token.token}"
            )
        except User.DoesNotExist:
            # IMPORTANT: do not reveal existence
            pass

        return Response({
            "detail": "If the email exists, a password reset link has been sent.",
            "success": True
        })

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(exclude=True)
    @swagger_auto_schema(
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                description="Password reset successful",
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
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token_obj"]
        new_password = serializer.validated_data["new_password"]

        user = reset_token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset_token.is_used = True
        reset_token.save(update_fields=["is_used"])

        return Response({"detail": "Password reset successful", "success": True})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token"),
            },
            required=["refresh"],
        ),
        responses={
            200: openapi.Response(
                description="Logged out successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Refresh token required",
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
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required", "success": False}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"detail": "Logged out successfully", "success": True})

class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    @swagger_auto_schema(
        auto_schema=None,
        responses={
            200: openapi.Response(
                description="Account deactivated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Account already deactivated",
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
        user = request.user

        if user.state == UserState.DEACTIVATED:
            return Response(
                {"detail": "Account already deactivated", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.state = UserState.DEACTIVATED
        user.deactivated_at = timezone.now()
        user.save(update_fields=["state", "deactivated_at"])

        return Response({"message": "Account deactivated", "success": True})

class ReactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(exclude=True)
    @swagger_auto_schema(
        auto_schema=None,
        responses={
            200: openapi.Response(
                description="Account reactivated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Account is not deactivated",
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
        user = request.user

        if user.state != UserState.DEACTIVATED:
            return Response(
                {"detail": "Account is not deactivated", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.state = UserState.ACTIVE
        user.deactivated_at = None
        user.save(update_fields=["state", "deactivated_at"])

        return Response({"message": "Account reactivated", "success": True})

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(exclude=True)
    @swagger_auto_schema(
        auto_schema=None,
        responses={
            200: openapi.Response(
                description="Account deleted permanently",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: openapi.Response(
                description="Account already deleted",
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
        user = request.user

        if user.state == UserState.DELETED:
            return Response(
                {"detail": "Account already deleted", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        anonymize_user(user)

        return Response(
            {"message": "Account deleted permanently", "success": True},
            status=status.HTTP_200_OK
        )

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Current user details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                        "phone": openapi.Schema(type=openapi.TYPE_STRING),
                        "full_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "date_of_birth": openapi.Schema(type=openapi.TYPE_STRING, format="date", nullable=True),
                        "gender": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "role": openapi.Schema(type=openapi.TYPE_STRING),
                        "state": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_email_verified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "is_phone_verified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "terms_accepted": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "terms_accepted_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", nullable=True),
                        "terms_version": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "onboarding_complete": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            401: openapi.Response(
                description="Unauthorized",
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
        serializer = UserMeSerializer(request.user)
        return Response({
            **serializer.data,
            "success": True
        })


############## ADMIN APIs ##############

class AdminUserListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminUserListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = AdminUserListPagination

    def get(self, request, role):
        if role not in [UserRole.PATIENT, UserRole.DOCTOR]:
            return Response(
                {
                    "detail": "Invalid role. Must be 'patient' or 'doctor'",
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        status_filter = request.query_params.get("status", None)
        users = User.objects.filter(role=role)
        
        if status_filter and role == UserRole.PATIENT:
            if status_filter not in ["active", "inactive"]:
                return Response(
                    {
                        "detail": "Invalid status. Must be 'active' or 'inactive'",
                        "success": False
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            users = users.filter(is_active=(status_filter=="active"))

        users = users.order_by('-created_at')
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserListSerializer(paginated_users, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True

        return Response(response_data)










# class DoctorRegistrationView(APIView):
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser, FormParser]

#     @swagger_auto_schema(
#         request_body=DoctorRegistrationSerializer,
#         responses={
#             201: openapi.Response(
#                 description="Doctor registered successfully",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "id": openapi.Schema(type=openapi.TYPE_STRING),
#                         "role": openapi.Schema(type=openapi.TYPE_STRING),
#                         "state": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             400: openapi.Response(
#                 description="Validation error",
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
#         serializer = DoctorRegistrationSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         is_email_verified = serializer.validated_data.get("is_email_verified", False)
#         is_phone_verified = serializer.validated_data.get("is_phone_verified", False)
#         if not (is_email_verified or is_phone_verified):
#             return Response(
#                 {"detail": "Email or phone must be verified to register as a doctor", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user = serializer.save(role=UserRole.DOCTOR)

#         return Response(
#             {
#                 "id": str(user.id),
#                 "role": user.role,
#                 "state": user.state,
#                 "success": True
#             },
#             status=status.HTTP_201_CREATED
#         )

# class PatientRegistrationView(APIView):
#     permission_classes = [AllowAny]
#     parser_classes = [FormParser]


#     @swagger_auto_schema(
#         request_body=PatientRegistrationSerializer,
#         responses={
#             201: openapi.Response(
#                 description="Patient registered successfully",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "id": openapi.Schema(type=openapi.TYPE_STRING),
#                         "role": openapi.Schema(type=openapi.TYPE_STRING),
#                         "state": openapi.Schema(type=openapi.TYPE_STRING),
#                     },
#                 ),
#             ),
#             400: openapi.Response(
#                 description="Validation error",
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
#         if request.data.get("role") and request.data.get("role") != UserRole.PATIENT:
#             return Response(
#                 {"detail": "Invalid role for this endpoint", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         serializer = PatientRegistrationSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         is_email_verified = serializer.validated_data.get("is_email_verified", False)
#         is_phone_verified = serializer.validated_data.get("is_phone_verified", False)
#         if not (is_email_verified or is_phone_verified):
#             return Response(
#                 {"detail": "Email or phone must be verified to register as a patient", "success": False},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user = serializer.save(role=UserRole.PATIENT)


#         return Response(
#             {
#                 "id": str(user.id),
#                 "role": user.role,
#                 "state": user.state,
#                 "success": True
#             },
#             status=status.HTTP_201_CREATED
#         )





