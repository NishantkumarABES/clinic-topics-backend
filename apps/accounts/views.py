from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.serializers import (
    EmailLoginSerializer, PhoneOTPRequestSerializer, PhoneOTPVerifySerializer, SocialLoginSerializer, DoctorRegistrationSerializer, 
    PatientRegistrationSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, EmailOTPRequestSerializer, 
    EmailOTPVerifySerializer
)
from apps.accounts.services import (
    activate_user_if_eligible, resolve_social_user, create_password_reset_token, send_email_otp, send_phone_otp,
    get_tokens_for_user, can_resend_otp, anonymize_user
)
from apps.accounts.social_providers import social_provider_verification
from apps.accounts.models import User
from apps.accounts.constants import UserState, UserRole




class EmailOTPRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailOTPRequestSerializer,
        responses={200: "EmailOTPRequestResponseSerializer data"},
    )
    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = send_email_otp(email)
        return Response({"detail": "OTP sent to email", "testing-otp": otp})

class EmailOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailOTPVerifySerializer,
        responses={200: "EmailOTPVerifyResponseSerializer data"},
    )
    def post(self, request):
        serializer = EmailOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_valid = serializer.validated_data["is_valid"]
        otp_obj = serializer.validated_data["otp_obj"]
        
        try:
            if not is_valid:
                return Response(
                    {"detail": "Invalid OTP"},
                    status=400
                )
            otp_obj.mark_as_used()
            return Response({"detail": "Email verified successfully"})
        except User.DoesNotExist:
            return Response(
                {"detail": "User with this email does not exist"},
                status=404
            )

class PhoneOTPRequestView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=PhoneOTPRequestSerializer,
        responses={200: "PhoneOTPRequestResponseSerializer data"},
    )
    
    def post(self, request):
        phone = request.data.get("phone")

        if not can_resend_otp(phone):
            return Response(
                {"detail": "Please wait before requesting another OTP"},
                status=429
            )
        
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        otp = send_phone_otp(phone)

        return Response({"detail": "OTP sent", "testing-otp": otp})

class PhoneOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=PhoneOTPVerifySerializer,
        responses={200: "PhoneOTPVerifyResponseSerializer data"},
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_valid = serializer.validated_data["is_valid"]
        otp_obj = serializer.validated_data["otp_obj"]
        
        try:
            if not is_valid:
                return Response(
                    {"detail": "Invalid OTP"},
                    status=400
                )
            otp_obj.mark_as_used()
            return Response({"detail": "Phone verified successfully"})

        except User.DoesNotExist:
            return Response(
                {"detail": "User with this phone number does not exist"},
                status=404
            )


class DoctorRegistrationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=DoctorRegistrationSerializer,
        responses={201: "RegistrationResponseSerializer data"},
    )
    def post(self, request):
        serializer = DoctorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_email_verified = serializer.validated_data.get("is_email_verified", False)
        is_phone_verified = serializer.validated_data.get("is_phone_verified", False)
        if not (is_email_verified or is_phone_verified):
            return Response(
                {"detail": "Email or phone must be verified to register as a doctor"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save(role=UserRole.DOCTOR)
        
        return Response(
            {
                "id": str(user.id),
                "role": user.role,
                "state": user.state,
            },
            status=status.HTTP_201_CREATED
        )

class PatientRegistrationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [FormParser]


    @swagger_auto_schema(
        request_body=PatientRegistrationSerializer,
        responses={201: "RegistrationResponseSerializer data"},
    )
    def post(self, request):
        if request.data.get("role") and request.data.get("role") != UserRole.PATIENT:
            return Response(
                {"detail": "Invalid role for this endpoint"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_email_verified = serializer.validated_data.get("is_email_verified", False)
        is_phone_verified = serializer.validated_data.get("is_phone_verified", False)
        if not (is_email_verified or is_phone_verified):
            return Response(
                {"detail": "Email or phone must be verified to register as a patient"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save(role=UserRole.PATIENT)


        return Response(
            {
                "id": str(user.id),
                "role": user.role,
                "state": user.state
            },
            status=status.HTTP_201_CREATED
        )


class EmailLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=EmailLoginSerializer,
        responses={200: "EmailLoginResponseSerializer data"},
    )
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user:
            return Response(
                {"error": serializer.validated_data.get("error")}
            )

        remember_me = request.data.get("remember_me", False)
        access_token, refresh_token = get_tokens_for_user(user, remember_me)

        return Response({
            "access": access_token,
            "refresh": refresh_token,
            "user": {
                "id": str(user.id),
                "role": user.role,
                "state": user.state,
                "onboarding_complete": (
                    True if user.role == "admin" else
                    hasattr(user, "doctor_profile") if user.role == "doctor" else
                    hasattr(user, "patient_profile")
                )
            }
        })


class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=SocialLoginSerializer,
        responses={200: "SocialLoginResponseSerializer data"},
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
                "onboarding_complete": (
                    hasattr(user, "doctor_profile")
                    if user.role == UserRole.DOCTOR
                    else hasattr(user, "patient_profile")
                )
            }
        })

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=PasswordResetRequestSerializer,
        responses={200: "Reset email sent"}
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
            "detail": "If the email exists, a password reset link has been sent."
        })

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=PasswordResetConfirmSerializer,
        responses={200: "Password reset successful"}
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

        return Response({"detail": "Password reset successful"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required"}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"detail": "Logged out successfully"})


class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.state == UserState.DEACTIVATED:
            return Response(
                {"detail": "Account already deactivated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.state = UserState.DEACTIVATED
        user.deactivated_at = timezone.now()
        user.save(update_fields=["state", "deactivated_at"])

        return Response({"message": "Account deactivated"})

class ReactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.state != UserState.DEACTIVATED:
            return Response(
                {"detail": "Account is not deactivated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.state = UserState.ACTIVE
        user.deactivated_at = None
        user.save(update_fields=["state", "deactivated_at"])

        return Response({"message": "Account reactivated"})

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user

        if user.state == UserState.DELETED:
            return Response(
                {"detail": "Account already deleted"},
                status=status.HTTP_400_BAD_REQUEST
            )

        anonymize_user(user)

        return Response(
            {"message": "Account deleted permanently"},
            status=status.HTTP_200_OK
        )









