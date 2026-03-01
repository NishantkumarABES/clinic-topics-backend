from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.services import normalize_phone
from apps.accounts.models import User, EmailOTP, AuthProvider, UserDevice
from apps.accounts.constants import UserState, UserRole, UserState, DeviceType
from apps.accounts.services import send_doctor_invitation_email, assert_identity_available, verify_phone_otp
from apps.accounts.social_providers import social_provider_verification
from apps.profiles.models import DoctorProfile

class RegisterSerializer(serializers.Serializer):
    # -------- Device Fields --------
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.ChoiceField(
        choices=("android", "ios", "web"),
        required=False,
        allow_blank=True
    )

    # -------- Common User Fields --------
    role = serializers.ChoiceField(choices=[UserRole.DOCTOR, UserRole.PATIENT], required=False)
    full_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    country_code = serializers.CharField(required=False, default="+91")

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    terms_accepted = serializers.BooleanField()
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=("male", "female", "other"),
        required=False,
        allow_null=True
    )

    is_email_verified = serializers.BooleanField(required=False, default=False)
    is_phone_verified = serializers.BooleanField(required=False, default=False)

    # -------- Doctor-only Fields --------
    specialization = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    license_number = serializers.CharField(required=False, allow_blank=True)
    license_document = serializers.FileField(required=False)

    # -------- Social Fields --------
    via_social = serializers.BooleanField(default=False)
    provider = serializers.ChoiceField(
        choices=("google", "apple", "facebook"),
        required=False,
        allow_null=True
    )
    token = serializers.CharField(required=False, allow_blank=True)

    # ---------------- VALIDATION ----------------

    def validate(self, data):
        forced_role = self.context.get("forced_role")
        if forced_role:
            data["role"] = forced_role
        
        if "role" not in data:
            raise ValidationError({"role": "Role is required"})

        role = data["role"]
        via_social = data.get("via_social", False)

        # ---- Admin protection ----
        if role == UserRole.ADMIN:
            raise ValidationError({"role": "Admin cannot be registered publicly"})

        # ---- Social validation ----
        social_user = None
        if via_social:
            provider = data.get("provider")
            token = data.get("token")

            if not provider or not token:
                raise ValidationError("Provider and token are required for social signup")

            verifier = social_provider_verification.get(provider)
            if not verifier:
                raise ValidationError({"provider": "Unsupported social provider"})

            social_user = verifier(token)

            # Enforce email consistency (if provider supplies email)
            if social_user.email and social_user.email != data["email"]:
                raise ValidationError(
                    {"email": "Email does not match social account"}
                )

            # Social = email verified by default
            data["is_email_verified"] = True

        else:
            # ---- Password required for non-social ----
            password = data.get("password")
            if not password:
                raise ValidationError({"password": "Password is required"})
            validate_password(password)

        # ---- Verification rule ----
        if not (data.get("is_email_verified") or data.get("is_phone_verified")):
            raise ValidationError("Email or phone must be verified")

        # ---- Unique constraints ----
        assert_identity_available(email=data["email"], phone=data["phone"])
        
        # ---- Doctor-specific validation ----
        if role == UserRole.DOCTOR:
            required = ["specialization", "license_number", "years_of_experience"]
            errors = {
                field: "This field is required for doctor registration"
                for field in required if not data.get(field)
            }
            if errors:
                raise ValidationError(errors)

        # Attach social_user for use in create()
        data["_social_user"] = social_user
        return data

    # ---------------- CREATE ----------------

    @transaction.atomic
    def create(self, validated_data):
        social_user = validated_data.pop("_social_user", None)
        # ---- Extract device fields ----
        device_token = validated_data.pop("device_token", None)
        device_type = validated_data.pop("device_type", None)
        password = validated_data.pop("password", None)
        role = validated_data["role"]
        # by_admin = validated_data.get("by_admin", False)
        is_admin_request = self.context.get("is_admin_request", False)
        is_admin_creating_doctor = is_admin_request and role == UserRole.DOCTOR
        # Admin-created doctors start as inactive, they activate on first login
        # is_active = False if by_admin else True
        is_active = True

        user = User.objects.create_user(
            email=validated_data["email"],
            phone=validated_data["phone"],
            country_code=validated_data["country_code"],
            password=password,
            full_name=validated_data["full_name"],
            role=role,
            state=UserState.CREATED,
            terms_accepted=validated_data["terms_accepted"],
            terms_accepted_at=timezone.now(),
            terms_version="1.0.0",
            date_of_birth=validated_data.get("date_of_birth"),
            gender=validated_data.get("gender"),
            is_email_verified=validated_data.get("is_email_verified"),
            is_phone_verified=validated_data.get("is_phone_verified"),
            by_admin=is_admin_creating_doctor,
            is_active=is_active,
        )

        if role == UserRole.DOCTOR:
            DoctorProfile.objects.create(
                user=user,
                specialization=validated_data["specialization"],
                years_of_experience=validated_data["years_of_experience"],
                license_number=validated_data["license_number"],
                license_document=validated_data.get("license_document"),
            )

        if social_user:
            AuthProvider.objects.create(
                user=user,
                provider=social_user.provider,
                provider_user_id=social_user.provider_user_id,
                email=social_user.email,
            )
        
        # ---- Device registration (NEW) ----
        if device_token and device_type:
            from apps.accounts.models import UserDevice
            UserDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    "user": user,
                    "device_type": device_type,
                    "is_active": True,
                    "last_seen_at": timezone.now()
                }
            )
        if is_admin_creating_doctor:
            send_doctor_invitation_email(user, password)

        return user

class PhoneOTPRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=5, required=False, default="+91")
    create_account = serializers.BooleanField(required=False, default=False)

    def validate_phone(self, value):
        if not value.isdigit():
            raise ValidationError("Phone number must contain only digits")
        return value

    def validate(self, data):
        data["phone_number"] = normalize_phone(
            data["phone"],
            data.get("country_code", "+91")
        )
        return data

class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    country_code = serializers.CharField(max_length=5, required=False, default="+91")
    otp = serializers.CharField(max_length=6)
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.ChoiceField(
        choices=DeviceType.DEVICE_CHOICES,
        required=False
    )
    def validate(self, data):
        data["phone_number"] = normalize_phone(
            data["phone"],
            data.get("country_code", "+91")
        )
        return data

class EmailOTPRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    country_code = serializers.CharField(required=False, default="+91")
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()

class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            otp_obj = EmailOTP.objects.filter(
                email=data["email"],
                is_used=False
            ).latest("created_at")
        except EmailOTP.DoesNotExist:
            raise ValidationError("Invalid OTP")

        if otp_obj.attempts >= otp_obj.MAX_ATTEMPTS:
            raise ValidationError("OTP locked due to too many attempts")

        if not otp_obj.is_valid():
            raise ValidationError("OTP expired")

        if otp_obj.otp != data["otp"]:
            otp_obj.register_failure()
            raise ValidationError("Invalid OTP")

        data["otp_obj"] = otp_obj
        return data

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.ChoiceField(
        choices=DeviceType.DEVICE_CHOICES,
        required=False
    )

    def validate(self, data):
        email = data["email"].lower()
        password = data["password"]

        # Fetch user by email
        user = User.objects.filter(email=email).first()

        if not user:
            raise ValidationError("user with this email does not exist")

        # Manually verify password (works even if user.is_active=False)
        if not user.check_password(password):
            raise ValidationError("Invalid email or password")
 
        if not user.can_authenticate():
            raise ValidationError("User with this email does not exist")
            
        # If admin-created doctor logging in first time → activate
        if user.by_admin and not user.is_active:
            user.is_active = True
            user.state = UserState.ACTIVE
            user.save(update_fields=["is_active", "state"])

        data["user"] = user
        return data

class SocialLoginSerializer(serializers.Serializer):
    device_token = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.ChoiceField(
        choices=DeviceType.DEVICE_CHOICES,
        required=False
    )
    provider = serializers.ChoiceField(
        choices=("google", "apple", "facebook")
    )
    token = serializers.CharField()
    remember_me = serializers.BooleanField(required=False)

class UserMeSerializer(serializers.ModelSerializer):
    onboarding_complete = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "country_code",
            "full_name", "date_of_birth", "gender",
            "role", "state", "is_email_verified",
            "is_phone_verified", "terms_accepted",
            "terms_accepted_at", "terms_version",
            "onboarding_complete", "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_onboarding_complete(self, obj):
        if obj.role == UserRole.ADMIN:
            return True
        elif obj.role == UserRole.DOCTOR:
            return hasattr(obj, "doctor_profile")
        elif obj.role == UserRole.PATIENT:
            return hasattr(obj, "patient_profile")
        return False

class DoctorProfileListSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "credentials",
            "specialization",
            "years_of_experience",
            "license_number",
            "medical_council",
            "clinic_name",
            "clinic_address",
            "clinic_location",
            "consultation_fee",
            "premium_online_fee",
            "consultation_duration_minutes",
            "bio",
            "profile_photo",
            "average_rating",
        ]

    def get_average_rating(self, obj):
        return obj.average_rating()

class UserListSerializer(serializers.ModelSerializer):
    doctor_profile = DoctorProfileListSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "country_code",
            "full_name", "date_of_birth", "gender",
            "state", "is_email_verified", "is_phone_verified",
            "is_active", "created_at", "updated_at",
            "doctor_profile",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Hide doctor_profile if user is not a doctor
        if instance.role != UserRole.DOCTOR:
            data.pop("doctor_profile", None)

        return data

class UserUpdateSerializer(serializers.ModelSerializer):
    # Doctor profile fields (optional, only for doctors)
    specialization = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    license_number = serializers.CharField(required=False, allow_blank=True)
    clinic_address = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "full_name", "phone", "country_code", "date_of_birth",
            "gender", "is_active", "specialization", "years_of_experience",
            "license_number", "clinic_address", "website_url"
        ]

    def validate_phone(self, value):
        # Check if phone already exists for another user
        user = self.instance
        if User.objects.filter(phone=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value
    
    def validate_email(self, value):
        # Check if email already exists for another user
        user = self.instance
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Email already registered")
        return value


    @transaction.atomic
    def update(self, instance, validated_data):
        # Extract doctor profile fields
        doctor_fields = {
            "specialization": validated_data.pop("specialization", None),
            "years_of_experience": validated_data.pop("years_of_experience", None),
            "license_number": validated_data.pop("license_number", None),
            "clinic_address": validated_data.pop("clinic_address", None),
            "website_url": validated_data.pop("website_url", None),
        }
        updatation_time = timezone.now()

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_at = updatation_time
        instance.save()

        # Update doctor profile if user is a doctor and profile exists
        if instance.role == UserRole.DOCTOR and hasattr(instance, 'doctor_profile'):
            doctor_profile = instance.doctor_profile
            for field, value in doctor_fields.items():
                if value is not None:
                    setattr(doctor_profile, field, value)
            doctor_profile.updated_at = updatation_time
            doctor_profile.save()

        return instance

class IdentityCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False, default="+91")

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise ValidationError("Email or phone is required")
        return data

class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False, default="+91")

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise ValidationError("Email or phone is required")

        if data.get("phone"):
            data["phone_number"] = normalize_phone(
                data["phone"],
                data.get("country_code", "+91")
            )

        return data

class ForgotPasswordVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False, default="+91")
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise ValidationError("Email or phone is required")

        if data.get("email"):
            try:
                otp_obj = EmailOTP.objects.filter(
                    email=data["email"],
                    is_used=False
                ).latest("created_at")
            except EmailOTP.DoesNotExist:
                raise ValidationError("Invalid OTP")

            if otp_obj.attempts >= otp_obj.MAX_ATTEMPTS:
                raise ValidationError("OTP locked")

            if not otp_obj.is_valid():
                raise ValidationError("OTP expired")

            if otp_obj.otp != data["otp"]:
                otp_obj.register_failure()
                raise ValidationError("Invalid OTP")

            data["otp_obj"] = otp_obj

        else:
            phone_number = normalize_phone(
                data["phone"],
                data.get("country_code", "+91")
            )

            otp_obj = verify_phone_otp(
                phone=phone_number,
                otp=data["otp"]
            )

            data["otp_obj"] = otp_obj
            data["phone_number"] = phone_number

        return data

class ForgotPasswordSetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    country_code = serializers.CharField(required=False, default="+91")
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise ValidationError("Email or phone is required")
        return data

class AdminForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class AdminForgotPasswordVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    
    def validate(self, data):
        try:
            otp_obj = EmailOTP.objects.filter(
                email="nishant543099@gmail.com",  # data["email"],
                is_used=False
            ).latest("created_at")
        except EmailOTP.DoesNotExist:
            raise ValidationError("Invalid OTP")

        if otp_obj.attempts >= otp_obj.MAX_ATTEMPTS:
            raise ValidationError("OTP locked")

        if not otp_obj.is_valid():
            raise ValidationError("OTP expired")

        data["otp_obj"] = otp_obj
        return data

#########################   Response Serializers    #########################

class StandardResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    success = serializers.BooleanField()

    class Meta:
        ref_name = "AccountsStandardResponseSerializer"

class OTPDataSerializer(serializers.Serializer):
    """Data returned in OTP responses (debug mode only)."""
    testing_otp = serializers.CharField(required=False, help_text="OTP code (DEBUG mode only)")

class OTPResponseSerializer(serializers.Serializer):
    """Response for OTP request endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = OTPDataSerializer(allow_null=True, required=False)
    success = serializers.BooleanField(help_text="Success status")

class AuthDataSerializer(serializers.Serializer):
    """Auth data containing tokens and user info."""
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserMeSerializer()

class LoginResponseSerializer(serializers.Serializer):
    """Response for login endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = AuthDataSerializer()
    success = serializers.BooleanField(help_text="Success status")

class RegisterResponseSerializer(serializers.Serializer):
    """Response for registration endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = AuthDataSerializer()
    success = serializers.BooleanField(help_text="Success status")

class UserMeResponseSerializer(serializers.Serializer):
    """Response for /me endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = UserMeSerializer()
    success = serializers.BooleanField(help_text="Success status")

class LogoutRequestSerializer(serializers.Serializer):
    """Request body for logout endpoint."""
    refresh = serializers.CharField(help_text="Refresh token to blacklist")


##################  Change password serializers ###################

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        user = self.context["request"].user
        
        if not user.check_password(data["old_password"]):
            raise ValidationError("Old password is incorrect")
        
        if data["old_password"] == data["new_password"]:
            raise ValidationError("New password cannot be same as old password")
        
        return data

class AdminChangePasswordSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise ValidationError("User not found")
        self.context["target_user"] = user
        return value

#####################################################################

class UserDeviceRegisterSerializer(serializers.Serializer):
    device_token = serializers.CharField(max_length=512)
    device_type = serializers.ChoiceField(
        choices=DeviceType.DEVICE_CHOICES
    )

    def create(self, validated_data):
        user = self.context["request"].user

        device, _ = UserDevice.objects.update_or_create(
            device_token=validated_data["device_token"],
            defaults={
                "user": user,
                "device_type": validated_data["device_type"],
                "is_active": True,
                "last_seen_at": timezone.now()
            }
        )
        return device

class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class CommonSuccessResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = serializers.DictField()
    success = serializers.BooleanField()

class CommonErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    success = serializers.BooleanField()






















