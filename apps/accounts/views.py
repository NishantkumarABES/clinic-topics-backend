from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers import (
    EmailLoginSerializer, PhoneOTPRequestSerializer, PhoneOTPVerifySerializer, SocialLoginSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, EmailOTPRequestSerializer, EmailOTPVerifySerializer, RegisterSerializer, UserMeSerializer,
    UserListSerializer, UserUpdateSerializer, LoginResponseSerializer, RegisterResponseSerializer, ChangePasswordSerializer,
    AdminChangePasswordSerializer, UserDeviceRegisterSerializer
)
from apps.accounts.services import (
    activate_user_if_eligible, resolve_social_user, create_password_reset_token, send_email_otp, send_phone_otp,
    get_tokens_for_user, can_resend_otp, anonymize_user, get_object_or_404, verify_phone_otp
)
from apps.accounts.social_providers import social_provider_verification
from apps.accounts.models import User
from apps.accounts.constants import UserState, UserRole
from core.permissions import IsAdmin
from config import settings


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
        responses={200: "OTP sent"}
    )
    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]

        if not can_resend_otp(phone):
            return Response(
                {"detail": "Please wait before requesting another OTP", "success": False},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        otp = send_phone_otp(phone)

        response = {"detail": "OTP sent", "success": True}

        # 🔐 Only expose OTP in DEBUG
        if settings.DEBUG:
            response["testing_otp"] = otp

        return Response(response)

class PhoneOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=PhoneOTPVerifySerializer,
        responses={200: "Phone verified"}
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        verify_phone_otp(phone=phone_number, otp=otp)

        return Response({"detail": "Phone verified successfully", "success": True})

class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        consumes=["multipart/form-data"],
        responses={
            201: RegisterResponseSerializer,
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
                "user": UserMeSerializer(user).data,
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )


class EmailLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailLoginSerializer,
        responses={
            200: LoginResponseSerializer
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
            "user": UserMeSerializer(user).data,
            "success": True
        })

class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=SocialLoginSerializer,
        responses={
            200: LoginResponseSerializer
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
                    "registration_required": True
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.can_authenticate():
            raise AuthenticationFailed("User account is inactive")

        # 3️⃣ Activate if eligible
        activate_user_if_eligible(user)

        # 4️⃣ Generate tokens
        access_token, refresh_token = get_tokens_for_user(user, remember_me)

        # 5️⃣ Response
        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": UserMeSerializer(user).data,
            "success": True
        })

class PhoneLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=PhoneOTPVerifySerializer,
        responses={
            200: LoginResponseSerializer
        }
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        verify_phone_otp(phone=phone_number, otp=otp)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this phone number does not exist", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified"])

        access, refresh = get_tokens_for_user(user)

        return Response({
            "access": access,
            "refresh": refresh,
            "user": UserMeSerializer(user).data,
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
            200: UserMeSerializer,
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

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, role):
        if role not in [UserRole.PATIENT, UserRole.DOCTOR]:
            return Response(
                {
                    "detail": "Invalid role. Must be 'patient' or 'doctor'",
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        search_term = request.query_params.get("search", None)
        speciality = request.query_params.get("speciality", None)
        status_filter = request.query_params.get("status", None)
        by_admin = request.query_params.get("by_admin", False)
        ordering = request.query_params.get("ordering", "-created_at")

        users = User.objects.filter(role=role)

        # Optimize query for doctors to include doctor_profile
        if role == UserRole.DOCTOR:
            users = users.select_related('doctor_profile')
        
        if by_admin and UserRole.DOCTOR:
            users = users.filter(by_admin=(by_admin=='true'))

        if search_term:
            users = users.filter(
                Q(full_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )
        
        if speciality:
            print(speciality)
            users = users.filter(doctor_profile__specialization__icontains=speciality)

        if status_filter and status_filter not in ["active", "inactive"]:
            return Response(
                {
                    "detail": "Invalid status. Must be 'active' or 'inactive'",
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if status_filter:
            users = users.filter(is_active=(status_filter=="active"))
        
        users = users.order_by(ordering)
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserListSerializer(paginated_users, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True

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
        updated_user = serializer.save()

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

    @swagger_auto_schema(request_body=ChangePasswordSerializer)
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
            {"message": "Device registered successfully", "success": True},
            status=status.HTTP_201_CREATED
        )

