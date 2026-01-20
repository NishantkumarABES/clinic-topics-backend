from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.db.models import Q, Index
from django.utils import timezone

from core.models import TimeStampedUUIDModel
from apps.accounts.constants import UserRole, UserState, DeviceType

class UserManager(BaseUserManager):
    def create_user(self, email, phone, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError("Either email or phone is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("state", UserState.ACTIVE)
        extra_fields.setdefault("terms_accepted", True)
        extra_fields.setdefault("terms_accepted_at", timezone.now())
        extra_fields.setdefault("terms_version", "1.0.0")
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("is_phone_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, phone="0000000000", password=password, **extra_fields)

    def create_admin_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("state", UserState.ACTIVE)

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )

class User(AbstractBaseUser, PermissionsMixin, TimeStampedUUIDModel):
    username = None

    # Identity
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    country_code = models.CharField(max_length=5, default="+91")
    full_name = models.CharField(max_length=255)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Personal
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("other", "Other")],
        null=True,
        blank=True
    )
    # Legal
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_version = models.CharField(max_length=50, null=True, blank=True)

    # Platform
    role = models.CharField(max_length=20, choices=UserRole.CHOICES)
    state = models.CharField(
        max_length=20,
        choices=UserState.CHOICES,
        default=UserState.CREATED
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)

    # Verification
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    by_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def can_authenticate(self):
        return self.state not in {
            UserState.SUSPENDED,
            UserState.DEACTIVATED,
            UserState.DELETED
        }
    
    def is_profile_complete(self):
        return all([
            self.full_name,
            self.gender,
            self.date_of_birth,
        ])

    def __str__(self):
        return f"{self.full_name} ({self.role})"

class UserDevice(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="devices"
    )

    device_token = models.CharField(
        max_length=512,
        unique=True,
        help_text="Push notification token from FCM/APNs"
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.DEVICE_CHOICES
    )

    is_active = models.BooleanField(default=True)

    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_devices"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["device_token"]),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.device_type}"

class AuthProvider(TimeStampedUUIDModel):
    PROVIDER_GOOGLE = "google"
    PROVIDER_APPLE = "apple"
    PROVIDER_FACEBOOK = "facebook"

    PROVIDER_CHOICES = (
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_APPLE, "Apple"),
        (PROVIDER_FACEBOOK, "Facebook"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="auth_providers"
    )

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES
    )

    provider_user_id = models.CharField(max_length=255)

    email = models.EmailField(null=True, blank=True)

    class Meta:
        unique_together = ("provider", "provider_user_id")

    def __str__(self):
        return f"{self.provider} → {self.user_id}"

class PhoneOTP(TimeStampedUUIDModel):
    phone = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Canonical phone number including country code, e.g. +911234567890"
    )

    otp = models.CharField(
        max_length=6,
        help_text="Numeric OTP"
    )

    expires_at = models.DateTimeField(
        db_index=True
    )

    is_used = models.BooleanField(
        default=False,
        db_index=True
    )
    MAX_ATTEMPTS = 5
    attempts = models.PositiveIntegerField(default=0)
    class Meta:
        indexes = [
            Index(fields=["phone", "otp", "is_used"]),
            Index(fields=["expires_at"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Phone OTP"
        verbose_name_plural = "Phone OTPs"

    def is_valid(self) -> bool:
        return (
            not self.is_used
            and timezone.now() <= self.expires_at
        )

    def register_failure(self):
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.is_used = True
        self.save(update_fields=["attempts", "is_used"])

    def marks_as_used(self):
        self.is_used = True
        self.save()

    @transaction.atomic
    def consume(self):
        otp = (
            PhoneOTP.objects
            .select_for_update()
            .get(id=self.id)
        )

        if otp.is_used:
            raise ValidationError("OTP already used")

        if timezone.now() > otp.expires_at:
            raise ValidationError("OTP expired")

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        return otp

    @classmethod
    def cleanup_expired(cls):
        return cls.objects.filter(
            Q(is_used=True) | Q(expires_at__lt=timezone.now())
        ).delete()

    def __str__(self):
        return f"OTP({self.phone})"

class EmailOTP(TimeStampedUUIDModel):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    MAX_ATTEMPTS = 5

    def is_valid(self):
        return (
            not self.is_used and 
            timezone.now() <= self.expires_at
        )
    
    def register_failure(self):
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.is_used = True
        self.save(update_fields=["attempts", "is_used"])

    def mark_as_used(self):
        self.is_used = True
        self.save()

    def __str__(self):
        return f"OTP for {self.email}"

class PasswordResetToken(TimeStampedUUIDModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return (
            not self.is_used and
            timezone.now() <= self.expires_at
        )


