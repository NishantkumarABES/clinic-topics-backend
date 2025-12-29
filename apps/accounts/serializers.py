from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User, PhoneOTP, PasswordResetToken, EmailOTP
from apps.accounts.constants import UserState, UserRole, UserState
from apps.profiles.models import DoctorProfile




class PatientRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=("male", "female", "other"), required=False, allow_null=True)
    terms_accepted = serializers.BooleanField(required=True)
    is_email_verified = serializers.BooleanField(required=False, default=False)
    is_phone_verified = serializers.BooleanField(required=False, default=False)
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_role(self, value):
        if value == UserRole.ADMIN:
            raise serializers.ValidationError(
                "Admin accounts cannot be created via public registration"
            )
        return value
    

    def create(self, validated_data):
        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
            role=validated_data["role"],
            state=UserState.CREATED,
            date_of_birth=validated_data.get("date_of_birth"),
            gender=validated_data.get("gender"),
            terms_accepted=validated_data.get("terms_accepted"),
            is_email_verified=validated_data.get("is_email_verified"),
            is_phone_verified=validated_data.get("is_phone_verified"),
        )
        return user

class DoctorRegistrationSerializer(serializers.ModelSerializer):
    # ---- User fields ----
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)
    terms_accepted = serializers.BooleanField(required=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=("male", "female", "other"), required=False, allow_null=True)
    is_email_verified = serializers.BooleanField(required=False, default=False)
    is_phone_verified = serializers.BooleanField(required=False, default=False)

    # ---- DoctorProfile fields ----
    specialization = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    license_number = serializers.CharField(required=False, allow_blank=True)
    license_document = serializers.FileField(required=False)

    class Meta:
        model = User
        fields = [
            "full_name", "email", "phone", "password", "terms_accepted", "is_email_verified", "date_of_birth", "gender",
            "is_phone_verified", "specialization", "years_of_experience", "license_number", "license_document",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    # ---------------- VALIDATIONS ---------------- #

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_role(self, value):
        if value != UserRole.DOCTOR:
            raise serializers.ValidationError(
                "Only doctor accounts can be created using this endpoint"
            )
        return value

    # ---------------- CREATE ---------------- #

    @transaction.atomic
    def create(self, validated_data):
        # ---- Extract DoctorProfile data ----
        doctor_data = {
            "specialization": validated_data.pop("specialization", None),
            "years_of_experience": validated_data.pop("years_of_experience", None),
            "license_number": validated_data.pop("license_number", None),
            "license_document": validated_data.pop("license_document", None),
        }

        # ---- Create User ----
        user = User.objects.create_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
            role=validated_data["role"],
            state=UserState.CREATED,
            terms_accepted=validated_data["terms_accepted"],
            date_of_birth=validated_data.get("date_of_birth"),
            gender=validated_data.get("gender"),
            is_email_verified=validated_data.get("is_email_verified"),
            is_phone_verified=validated_data.get("is_phone_verified"),
        )

        # ---- Create DoctorProfile ----
        DoctorProfile.objects.create(
            user=user,
            specializations=[doctor_data["specialization"]]
            if doctor_data["specialization"] else [],
            years_of_experience=doctor_data["years_of_experience"],
            license_number=doctor_data["license_number"],
            license_document=doctor_data["license_document"],
        )

        return user


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        # basic sanity check; extend later
        if not value.isdigit():
            raise ValidationError("Invalid phone number")
        return value

class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            otp_obj = PhoneOTP.objects.filter(
                phone=data["phone"],
                otp=data["otp"],
                is_used=False
            ).latest("created_at")
        except PhoneOTP.DoesNotExist:
            data["otp_obj"] = None
            data["message"] = "Invalid OTP or OTP already used"
            data["is_valid"] = False
            return data

        if not otp_obj.is_valid():
            data["otp_obj"] = otp_obj
            data["is_valid"] = False
            data["message"] = "OTP expired"
            return data
        
        if otp_obj.otp != data["otp"]:
            data["otp_obj"] = otp_obj
            data["is_valid"] = False
            data["message"] = "Invalid OTP"
            return data
    
        data["otp_obj"] = otp_obj
        data["is_valid"] = True
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
        user = authenticate(
            email=data["email"],
            password=data["password"]
        )
        if not user:
            data["error"] = "Invalid email or password"

        data["user"] = user
        return data

class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=("google", "apple", "facebook")
    )
    token = serializers.CharField()
    role = serializers.ChoiceField(
        choices=UserRole.CHOICES,
        required=False
    )
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




    