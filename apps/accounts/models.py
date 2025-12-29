from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone

from core.models import TimeStampedUUIDModel
from apps.accounts.constants import UserRole, UserState

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
    suspended_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    # Verification
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    

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
    phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return (
            not self.is_used and
            timezone.now() <= self.expires_at
        )

    def mark_as_used(self):
        self.is_used = True
        self.save()

    def __str__(self):
        return f"OTP for {self.phone}"

class EmailOTP(TimeStampedUUIDModel):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return (
            not self.is_used and 
            timezone.now() <= self.expires_at
        )

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


