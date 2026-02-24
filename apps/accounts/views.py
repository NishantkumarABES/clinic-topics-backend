from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers import (
    EmailLoginSerializer, PhoneOTPRequestSerializer, PhoneOTPVerifySerializer, SocialLoginSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailOTPRequestSerializer, EmailOTPVerifySerializer, RegisterSerializer, UserMeSerializer,
    UserListSerializer, UserUpdateSerializer, LoginResponseSerializer, RegisterResponseSerializer, ChangePasswordSerializer,
    AdminChangePasswordSerializer, UserDeviceRegisterSerializer, StandardResponseSerializer, OTPResponseSerializer,
    UserMeResponseSerializer, LogoutRequestSerializer, CommonSuccessResponseSerializer, CommonErrorResponseSerializer,
    TokenRefreshRequestSerializer, IdentityCheckSerializer, ForgotPasswordRequestSerializer, ForgotPasswordVerifySerializer, 
    ForgotPasswordSetSerializer
)
from apps.accounts.services import (
    activate_user_if_eligible, resolve_social_user, create_password_reset_token, send_email_otp, send_phone_otp,
    get_tokens_for_user, can_resend_otp, get_object_or_404, verify_phone_otp, mark_user_login
)
from apps.accounts.social_providers import social_provider_verification
from apps.accounts.models import User, UserDevice, AuthProvider
from apps.accounts.constants import UserState, UserRole
from core.permissions import IsAdmin
from core.api_responses import *
from config import settings



class EmailOTPRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Request OTP for email verification",
        request_body=EmailOTPRequestSerializer,
        responses={
            200: OTPResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        phone = serializer.validated_data.get("phone")
        full_name = serializer.validated_data.get("full_name")
        qs = User.objects.exclude(state=UserState.DELETED)

        phone_exists = qs.filter(phone=phone).exists() if phone else False

        # 🚫 Prevent sending OTP if identity already exists
        if phone_exists:
            msg = "Account already exists with this phone"
            return Response({
                "detail": msg,
                "data": {
                    "phone_exists": phone_exists
                },
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp = send_email_otp(email, full_name)
        except Exception as e:
            return Response({
                "detail": str(e),
                "data": None,
                "success": False
            })
        response = {
            "detail": "OTP sent to email",
            "data": None,
            "success": True
        }
        # 🔐 Only expose OTP in DEBUG
        if settings.DEBUG:
            response["data"] = {"testing_otp": otp}

        return Response(response)

class EmailOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify email with OTP",
        request_body=EmailOTPVerifySerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request):
        serializer = EmailOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_obj = serializer.validated_data["otp_obj"]
        otp_obj.mark_as_used()

        return Response({
            "detail": "Email verified successfully",
            "data": None,
            "success": True
        })

class PhoneOTPRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Request OTP for phone verification",
        request_body=PhoneOTPRequestSerializer,
        responses={
            200: OTPResponseSerializer,
            400: BAD_REQUEST_400,
            429: TOO_MANY_REQUESTS_429,
        },
    )
    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        email = serializer.validated_data.get("email")
        full_name = serializer.validated_data.get("full_name")
        phone_number = serializer.validated_data["phone_number"]
        create_account = serializer.validated_data["create_account"]

        qs = User.objects.exclude(state=UserState.DELETED)

        email_exists = qs.filter(email=email).exists() if email else False
        
        # 🚫 Prevent sending OTP if identity already exists
        if email_exists:
            msg = "Account already exists with this email"
            return Response({
                "detail": msg,
                "data": {
                    "email_exists": email_exists,
                },
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        if not create_account and User.objects.filter(
            phone=phone, state=UserState.DELETED
        ).exists():
            return Response(
                {
                    "detail": "User with this phone number does not exist",
                    "data": None,
                    "success": False
                }
            )

        if not can_resend_otp(phone=phone):
            return Response(
                {"detail": "Please wait before requesting another OTP", "data": None, "success": False},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        try:
            otp = send_phone_otp(phone=phone_number)
        except Exception as e:
            return Response({
                "detail": str(e),
                "data": None,
                "success": False
            })

        response = {"detail": "OTP sent", "data": None, "success": True}

        # 🔐 Only expose OTP in DEBUG
        if settings.DEBUG:
            response["data"] = {"testing_otp": otp}

        return Response(response)

class PhoneOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify phone with OTP",
        request_body=PhoneOTPVerifySerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        verify_phone_otp(phone=phone_number, otp=otp)

        return Response({"detail": "Phone verified successfully", "data": None, "success": True})

class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Register a new user (patient or doctor)",
        request_body=RegisterSerializer,
        consumes=["multipart/form-data"],
        responses={
            201: RegisterResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request, role):
        # ---- Normalize & validate role ----
        role = role.lower()
        
        if role not in dict(UserRole.CHOICES):
            return Response(
                {"detail": "Invalid role", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---- Inject role into request data ----
        # data = request.data.copy()
        # data = dict(request.data)
        # data["role"] = role

        is_admin_request = (
            request.user.is_authenticated and
            request.user.role == UserRole.ADMIN
        )

        serializer = RegisterSerializer(
            data=request.data,
            context={
                "is_admin_request": is_admin_request,
                "forced_role": role
            }
        )

        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False}
            )
        if is_admin_request and role == UserRole.DOCTOR:
            return Response(
                {"detail": "Doctor created and invitation email sent", "data": None, "success": True},
                status=status.HTTP_201_CREATED
            )
        access_token, refresh_token = get_tokens_for_user(user, False)
        return Response(
            {
                "detail": "User registered successfully",
                "data": {
                    "access": access_token,
                    "refresh": refresh_token,
                    "user": UserMeSerializer(user).data,
                },
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )

class EmailLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with email and password",
        request_body=EmailLoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
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
        device_token = serializer.validated_data.get("device_token")
        device_type = serializer.validated_data.get("device_type")
        if device_token and device_type:
            UserDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    "user": user,
                    "device_type": device_type,
                    "is_active": True,
                    "last_seen_at": timezone.now()
                }
            )
        remember_me = request.data.get("remember_me", False)
        access_token, refresh_token = get_tokens_for_user(user, remember_me)
        activate_user_if_eligible(user)
        mark_user_login(user)
        return Response({
            "detail" : "Logged in successfully",
            "data": {
                "access": access_token,
                "refresh": refresh_token,
                "user": UserMeSerializer(user).data
            },
            "success": True
        })

class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Login with social provider (Google, Apple, Facebook)",
        request_body=SocialLoginSerializer,
        responses={
            200: LoginResponseSerializer,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        },
    )
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        token = serializer.validated_data["token"]
        remember_me = serializer.validated_data.get("remember_me", False)

        verifier = social_provider_verification.get(provider)
        if not verifier:
            raise AuthenticationFailed("Unsupported social provider")

        # 1️⃣ Verify social token
        social_user = verifier(token)

        # 2️⃣ Resolve existing user
        
        user = resolve_social_user(social_user)
        if not user:
            return Response(
                {
                    "detail": "Registration required",
                    "data": {
                        "registration_required": True,
                        "provider": social_user.provider,
                        "provider_user_id": social_user.provider_user_id,
                        "email": social_user.email,
                    },
                    "success": True
                },
                status=status.HTTP_200_OK
            )

        if not user.can_authenticate():
            return Response(
                {
                    "detail": "Registration required",
                    "data": {
                        "registration_required": True,
                        "provider": social_user.provider,
                        "provider_user_id": social_user.provider_user_id,
                        "email": social_user.email,
                    },
                    "success": True
                },
                status=status.HTTP_200_OK
            )
            # return Response(
            #     {"detail": "User account is inactive", "data":None, "success": False}
            # )

        # 3️⃣ Activate if eligible
        activate_user_if_eligible(user)
        device_token = serializer.validated_data.get("device_token")
        device_type = serializer.validated_data.get("device_type")
        if device_token and device_type:
            UserDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    "user": user,
                    "device_type": device_type,
                    "is_active": True,
                    "last_seen_at": timezone.now()
                }
            )
        # 4️⃣ Generate tokens
        access_token, refresh_token = get_tokens_for_user(user, remember_me)
        mark_user_login(user)
        # 5️⃣ Response
        return Response({
            "detail" : "Logged in successfully",
            "data": {
                "access": access_token,
                "refresh": refresh_token,
                "user": UserMeSerializer(user).data
            },
            "success": True
        })

class PhoneLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with phone OTP",
        request_body=PhoneOTPVerifySerializer,
        responses={
            200: LoginResponseSerializer,
            400: BAD_REQUEST_400,
            404: NOT_FOUND_404,
        },
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        verify_phone_otp(phone=phone_number, otp=otp)

        try:
            user = User.objects.exclude(state=UserState.DELETED).get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "Registration required",
                    "data": {
                        "registration_required": True,
                        "phone": phone_number
                    },
                    "success": True
                },
                status=status.HTTP_200_OK
            )
            
        
        if not user.can_authenticate():
            return Response({
                "detail": "User account is inactive", 
                "data": None, "success": False
            })

        if not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])

        device_token = serializer.validated_data.get("device_token")
        device_type = serializer.validated_data.get("device_type")
        if device_token and device_type:
            UserDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    "user": user,
                    "device_type": device_type,
                    "is_active": True,
                    "last_seen_at": timezone.now()
                }
            )
        access_token, refresh_token = get_tokens_for_user(user)
        mark_user_login(user)
        activate_user_if_eligible(user)
        return Response({
            "detail" : "Logged in successfully",
            "data": {
                "access": access_token,
                "refresh": refresh_token,
                "user": UserMeSerializer(user).data
            },
            "success": True
        })
      
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    @swagger_auto_schema(
        operation_description="Request password reset email",
        request_body=PasswordResetRequestSerializer,
        responses={
            200: StandardResponseSerializer,
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
            "data": None,
            "success": True
        })

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(exclude=True)
    @swagger_auto_schema(
        operation_description="Confirm password reset with token",
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
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

        return Response({"detail": "Password reset successful", "data": None, "success": True})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Logout and blacklist refresh token",
        request_body=LogoutRequestSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required", "data": None, "success": False}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"detail": "Logged out successfully", "data": None, "success": True})

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
        operation_description="Permanently delete account",
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        user = request.user

        if user.state == UserState.DELETED:
            return Response(
                {"detail": "Account already deleted", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # 🔥 Remove social links FIRST
            AuthProvider.objects.filter(user=user).delete()
            # Optional but recommended:
            UserDevice.objects.filter(user=user).delete()
            # Soft delete user
            user.state = UserState.DELETED
            user.is_active = False
            user.save(update_fields=["state", "is_active"])

        # anonymize_user(user)
        return Response(
            {"detail": "Account deleted permanently", "data": None, "success": True},
            status=status.HTTP_200_OK
        )

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current user profile",
        responses={
            200: UserMeResponseSerializer,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response({
            "detail": "User profile retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class IdentityCheckView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Check if email or phone already registered",
        request_body=IdentityCheckSerializer,
        responses={200: StandardResponseSerializer},
    )
    def post(self, request):
        serializer = IdentityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")

        qs = User.objects.exclude(state=UserState.DELETED)

        email_exists = qs.filter(email=email).exists() if email else False
        phone_exists = qs.filter(phone=phone).exists() if phone else False

        if email_exists or phone_exists:

            if email_exists and phone_exists:
                msg = "Account already exists with this email and phone"
            elif email_exists:
                msg = "Account already exists with this email"
            else:
                msg = "Account already exists with this phone"

            return Response({
                "detail": msg,
                "data": {
                    "email_exists": email_exists,
                    "phone_exists": phone_exists
                },
                "success": False
            }, status=status.HTTP_200_OK)

        return Response({
            "detail": "Identity available",
            "data": {
                "email_exists": False,
                "phone_exists": False
            },
            "success": True
        })

class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Request OTP for forgot password (via email or phone)",
        request_body=ForgotPasswordRequestSerializer,
        responses={
            200: OTPResponseSerializer,
            400: BAD_REQUEST_400,
            429: TOO_MANY_REQUESTS_429,
        },
    )
    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")
        phone_number = serializer.validated_data.get("phone_number")

        user = None
        otp = None

        if email:
            user = User.objects.filter(
                email=email
            ).exclude(state=UserState.DELETED).first()

            if user:
                otp = send_email_otp(
                    email=email,
                    full_name=user.full_name,
                    forget_password=True
                )
            else:
                return Response(
                    {"detail": "User with this email does not exist", "data": None, "success": False},
                )

        elif phone:
            user = User.objects.filter(
                phone=phone
            ).exclude(state=UserState.DELETED).first()

            if user:
                otp = send_phone_otp(
                    phone_number,
                    forgot_password=False
                )
            else:
                return Response(
                    {"detail": "User with this phone does not exist", "data": None, "success": False},
                )


        response = {
            "detail": "If the account exists, an OTP has been sent.",
            "data": None,
            "success": True
        }

        if settings.DEBUG and user and otp:
            response["data"] = {"testing_otp": otp}

        return Response(response)

class ForgotPasswordVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify OTP for forgot password",
        request_body=ForgotPasswordVerifySerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request):
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_obj = serializer.validated_data["otp_obj"]
        otp_obj.mark_as_used() if hasattr(otp_obj, "mark_as_used") else None

        return Response({
            "detail": "OTP verified successfully",
            "data": None,
            "success": True
        })

class ForgotPasswordSetNewPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Set new password for forgot password",
        request_body=ForgotPasswordSetSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = ForgotPasswordSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")
        new_password = serializer.validated_data["new_password"]
        if email:
            user = User.objects.filter(
                email=email
            ).exclude(
                state=UserState.DELETED
            ).first()
        else:
            user = User.objects.filter(
                phone=phone
            ).exclude(
                state=UserState.DELETED
            ).first()

        if not user:
            return Response(
                {"detail": "User with this email or phone does not exist", "data": None, "success": False},
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({
            "detail": "Password reset successful",
            "data": None,
            "success": True
        })


############## ADMIN APIs ##############

class AdminUserListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

ordering_column_map = {
    "specialization" : "doctor_profile__specialization",
    "-specialization" : "-doctor_profile__specialization",
    "years_of_experience" : "doctor_profile__years_of_experience",
    "-years_of_experience" : "-doctor_profile__years_of_experience",
    "license_number" : "doctor_profile__license_number",
    "-license_number" : "-doctor_profile__license_number",
}

class AdminUserListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = AdminUserListPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, role):
        if role not in [UserRole.PATIENT, UserRole.DOCTOR]:
            return Response(
                {"detail": "Invalid role. Must be 'patient' or 'doctor'", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        search_term = request.query_params.get("search")
        speciality = request.query_params.get("speciality")
        status_filter = request.query_params.get("status")
        by_admin = request.query_params.get("by_admin")
        ordering = request.query_params.get("ordering", "-created_at")

        users = User.objects.filter(role=role)

        # Efficient join
        if role == UserRole.DOCTOR:
            users = users.select_related("doctor_profile")

        if by_admin is not None and role == UserRole.DOCTOR:
            users = users.filter(by_admin=(by_admin.lower() == "true"))

        if search_term:
            users = users.filter(
                Q(full_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )

        if speciality and role == UserRole.DOCTOR:
            users = users.filter(
                doctor_profile__specialization__icontains=speciality
            )

        if status_filter:
            if status_filter not in ["active", "inactive", "created", "deleted"]:
                return Response(
                    {"detail": "Invalid status. Must be 'active', 'inactive', 'created', or 'deleted'", "success": False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            users = users.filter(state=status_filter)

        users = users.order_by(ordering_column_map.get(ordering, ordering))

        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)

        serializer = UserListSerializer(paginated_users, many=True)

        response_data = paginator.get_paginated_response(serializer.data).data
        response_data["success"] = True
        response_data["detail"] = "User list fetched successfully"

        return Response(response_data)

class AdminAllUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = AdminUserListPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        search_term = request.query_params.get('search', '')
        users = User.objects.filter(role__in=[UserRole.PATIENT, UserRole.DOCTOR])
        users = users.order_by('-created_at')

        if search_term:
            users = users.filter(
                Q(full_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )
        
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserListSerializer(paginated_users, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True

        return Response(response_data)

class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, user_id):
        is_admin = request.user.is_staff
        print("IS ADMIN", is_admin)
        user_to_update = get_object_or_404(User, id=user_id)
        if is_admin and user_to_update.role == UserRole.PATIENT:
            return Response(
                {"detail": "Patients cannot be updated by admins", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if is_admin and user_to_update.role == UserRole.ADMIN:
            return Response(
                {"detail": "Admins cannot be updated by admins", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print("USER TO UPDATE", user_to_update.full_name)
        
        serializer = UserUpdateSerializer(
            user_to_update, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            updated_user = serializer.save()
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False}
            )

        # Prepare response data
        response_data = {
            "id": str(updated_user.id),
            "full_name": updated_user.full_name,
            "phone": updated_user.phone,
            "country_code": updated_user.country_code,
            "date_of_birth": updated_user.date_of_birth,
            "gender": updated_user.gender,
            "is_active": updated_user.is_active,
        }

        # Include doctor profile fields if applicable
        if updated_user.role == UserRole.DOCTOR and hasattr(updated_user, 'doctor_profile'):
            doctor_profile = updated_user.doctor_profile
            response_data.update({
                "specialization": doctor_profile.specialization,
                "years_of_experience": doctor_profile.years_of_experience,
                "license_number": doctor_profile.license_number,
                "clinic_address": doctor_profile.clinic_address,
            })

        return Response({
            "detail": "User updated successfully",
            "user": response_data,
            "success": True
        })

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Change current user password",
        request_body=ChangePasswordSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({
            "detail": "Password changed successfully",
            "data": None,
            "success": True
        })
    
class AdminChangePasswordView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(request_body=AdminChangePasswordSerializer, auto_schema=None)
    def post(self, request):
        serializer = AdminChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        target_user = serializer.context["target_user"]
        new_password = serializer.validated_data["new_password"]

        target_user.set_password(new_password)
        target_user.save(update_fields=["password"])

        return Response({
            "detail": f"Password changed for user {target_user.email}",
            "success": True
        })

class RegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Register device for push notifications",
        request_body=UserDeviceRegisterSerializer,
        responses={
            201: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        serializer = UserDeviceRegisterSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        device = serializer.save()
        device.last_seen_at = timezone.now()
        device.save(update_fields=["last_seen_at"])

        return Response(
            {"detail": "Device registered successfully", "data": None, "success": True},
            status=status.HTTP_201_CREATED
        )

class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        request_body=TokenRefreshRequestSerializer,
        responses={
            200: CommonSuccessResponseSerializer,
            401: CommonErrorResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            # If refresh successful
            if response.status_code == status.HTTP_200_OK:
                return Response({
                    "detail": "Token refreshed successfully",
                    "data": response.data,
                    "success": True
                }, status=status.HTTP_200_OK)

            # If unexpected non-200
            return Response({
                "detail": "Token refresh failed",
                "data": None,
                "success": False
            }, status=response.status_code)

        except Exception as e:
            return Response({
                "detail": str(e), "data": None, "success": False
            })

