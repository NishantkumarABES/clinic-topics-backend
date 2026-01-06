from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.services import normalize_phone
from apps.accounts.models import User, PasswordResetToken, EmailOTP, AuthProvider
from apps.accounts.constants import UserState, UserRole, UserState
from apps.profiles.models import DoctorProfile
from apps.accounts.social_providers import social_provider_verification

class RegisterSerializer(serializers.Serializer):
    # -------- Common User Fields --------
    role = serializers.ChoiceField(choices=[UserRole.DOCTOR, UserRole.PATIENT])
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

    # -------- Admin Flag --------
    by_admin = serializers.BooleanField(default=False)

    # ---------------- VALIDATION ----------------

    def validate(self, data):
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
        if User.objects.filter(email=data["email"]).exists():
            raise ValidationError({"email": "Email already registered"})

        if User.objects.filter(phone=data["phone"]).exists():
            raise ValidationError({"phone": "Phone already registered"})

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

        password = validated_data.pop("password", None)
        role = validated_data["role"]

        user = User.objects.create_user(
            email=validated_data["email"],
            phone=validated_data["phone"],
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
            by_admin=validated_data.get("by_admin", False),
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

        return user

class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    country_code = serializers.CharField(max_length=5, required=False, default="+91")

    def validate_phone(self, value):
        if not value.isdigit():
            raise ValidationError("Phone number must contain only digits")
        return value

    def validate(self, data):
        data["phone"] = normalize_phone(
            data["phone"],
            data.get("country_code", "+91")
        )
        return data

class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    country_code = serializers.CharField(max_length=5, required=False, default="+91")
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        data["phone_number"] = normalize_phone(
            data["phone"],
            data.get("country_code", "+91")
        )
        return data


class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)

    def validate(self, data):
        try:
            otp_obj = EmailOTP.objects.filter(
                email=data["email"],
                otp=data["otp"],
                is_used=False
            ).latest("created_at")
        except EmailOTP.DoesNotExist:
            data["otp_obj"] = None
            data["message"] = "Invalid OTP or OTP already used"
            data["is_valid"] = False
            return data
        
        if not otp_obj.is_valid():
            data["is_valid"] = False
            data["otp_obj"] = otp_obj
            data["message"] = "OTP expired"
            return data
        
        if otp_obj.otp != data["otp"]:
            data["is_valid"] = False
            data["otp_obj"] = otp_obj
            data["message"] = "Invalid OTP"
            return data
        
        data["otp_obj"] = otp_obj
        data["is_valid"] = True
        return data


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(required=False)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user: data["error"] = "Invalid email or password"
        data["user"] = user
        return data

class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=("google", "apple", "facebook")
    )
    token = serializers.CharField()
    remember_me = serializers.BooleanField(required=False)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        try:
            reset_token = PasswordResetToken.objects.get(
                token=data["token"],
                is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            raise ValidationError("Invalid or expired token")

        if not reset_token.is_valid():
            raise ValidationError("Token expired")

        data["reset_token_obj"] = reset_token
        return data

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


class UserListSerializer(serializers.ModelSerializer):
    license_number = serializers.SerializerMethodField()
    clinic_address = serializers.SerializerMethodField()
    specialization = serializers.SerializerMethodField()
    years_of_experience = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "country_code",
            "full_name", "date_of_birth", "gender", "state", "is_email_verified",
            "is_phone_verified", "is_active", "created_at", "updated_at",
            "license_number", "clinic_address",
            "specialization", "years_of_experience",
        ]
        read_only_fields = fields

    def get_license_number(self, obj):
        if obj.role == UserRole.DOCTOR and hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.license_number
        return None

    def get_clinic_address(self, obj):
        if obj.role == UserRole.DOCTOR and hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.clinic_address
        return None

    def get_specialization(self, obj):
        if obj.role == UserRole.DOCTOR and hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.specialization
        return None

    def get_years_of_experience(self, obj):
        if obj.role == UserRole.DOCTOR and hasattr(obj, 'doctor_profile'):
            return obj.doctor_profile.years_of_experience
        return None

class UserUpdateSerializer(serializers.ModelSerializer):
    # Doctor profile fields (optional, only for doctors)
    specialization = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    license_number = serializers.CharField(required=False, allow_blank=True)
    clinic_address = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "full_name", "phone", "country_code", "date_of_birth",
            "gender", "is_active", "specialization", "years_of_experience",
            "license_number", "clinic_address"
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




#########################   Response Serializers    #########################

class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserMeSerializer()
    success = serializers.BooleanField()

class RegisterResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserMeSerializer()
    success = serializers.BooleanField()




























