import os, random, secrets, requests
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from datetime import timedelta

from apps.accounts.constants import UserState
from apps.accounts.models import User, AuthProvider, PhoneOTP, PasswordResetToken, EmailOTP
from config.settings import OTP_EXPIRY_MINUTES

def assert_identity_available(email=None, phone=None):
    qs = User.objects.exclude(state=UserState.DELETED)

    if email and qs.filter(email=email).exists():
        raise ValidationError("Email already linked to another account")

    if phone and qs.filter(phone=phone).exists():
        raise ValidationError("Phone already linked to another account")

def get_user_by_email(email) -> User | None:
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None

def get_user_by_phone(phone) -> User | None:
    try:
        return User.objects.get(phone=phone)
    except User.DoesNotExist:
        return None

def is_user_profile_complete(user):
    return all([
        user.full_name,
        user.gender,
        user.date_of_birth,
    ])

def activate_user_if_eligible(user):
    if user.state != UserState.CREATED:
        return user

    if not user.is_profile_complete():
        return

    if user.role == "patient":
        if hasattr(user, "patient_profile"):
            user.state = UserState.ACTIVE
            user.save(update_fields=["state"])

    elif user.role == "doctor":
        if hasattr(user, "doctor_profile"):
            user.state = UserState.ACTIVE
            user.save(update_fields=["state"])

    return user

def generate_otp():
    return f"{random.randint(1000, 9999)}"

def send_phone_otp(phone: str) -> dict:
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    print(phone, otp, expires_at)
    PhoneOTP.objects.create(
        phone=phone, otp=otp,
        expires_at=expires_at
    )
    if phone.startswith("+91"):
        api_key = os.environ.get("SMS_API_KEY")
        sid = os.environ.get("SMS_SENDER_ID")
        tid = os.environ.get("SMS_TEMPLATE_ID")

        if not all([api_key, sid, tid]):
            raise ValueError("Missing SMS environment variables")

        msg = f"{otp} is your ClinicTopics verification code. Thanks, Team Promedica Health Communication Pvt. Ltd."

        url = (
            "https://smsapi.edumarcsms.com/api/v1/sendsms?"
            f"apikey={api_key}&senderId={sid}&message={msg}&number=[{phone}]&templateId={tid}"
        )
    else:
        api_key = os.environ.get("INTERNATION_API_KEY")
        if not api_key:
            raise ValueError("Missing INTERNATIONAL SMS API KEY")

        msg = f"{otp} is your account verification code PROMEDICA HEALTH COMMUNICATION PRIVATE LIMITED"

        url = (
            "https://www.smsgatewayhub.com/api/mt/SendSMS?"
            f"APIKey={api_key}&senderid=SMSHUB&channel=INT&DCS=0&flashsms=0"
            f"&number={phone}&text={msg}&route=16"
        )
    response = requests.get(url, timeout=10)
    return otp

def normalize_phone(phone: str, country_code: str = "+91") -> str:
    phone = phone.strip()
    if phone.startswith("+"):
        return phone
    return f"{country_code}{phone}"

def verify_phone_otp(phone: str, otp: str) -> PhoneOTP:
    with transaction.atomic():
        try:
            otp_obj = (
                PhoneOTP.objects
                .select_for_update()
                .filter(phone=phone, otp=otp, is_used=False)
                .latest("created_at")
            )
        except PhoneOTP.DoesNotExist:
            raise ValidationError("Invalid or already used OTP")

        if otp_obj.attempts >= otp_obj.MAX_ATTEMPTS:
            raise ValidationError("OTP locked due to too many attempts")

        if not otp_obj.is_valid():
            raise ValidationError("OTP expired")

        otp_obj.marks_as_used()
        return otp_obj

def send_email_otp(email):
    otp = generate_otp()
    EmailOTP.objects.create(
        email=email,
        otp=otp,
        expires_at=timezone.now() + timedelta(minutes=5)
    )
    # send_mail(
    #     "Clinic Topics Verification Code",
    #     f"Your verification code is {otp}",
    #     None,
    #     [email],
    # )
    return otp

def can_resend_otp(phone):
    last_otp = PhoneOTP.objects.filter(phone=phone).order_by("-created_at").first()
    if last_otp and (timezone.now() - last_otp.created_at).seconds < 30:
        return False
    return True

def resolve_social_user(social_user):
    """
    Resolves a social login to an existing user.
    Priority:
    1) Existing AuthProvider link
    2) Existing user with same email (auto-link)
    3) None → registration required
    """
    # Case 1: Already linked social account
    try:
        auth = AuthProvider.objects.select_related("user").get(
            provider=social_user.provider,
            provider_user_id=social_user.provider_user_id
        )
        return auth.user
    except AuthProvider.DoesNotExist:
        pass

    # Case 2: No link exists, but email matches an existing user
    if social_user.email:
        try:
            user = User.objects.get(email=social_user.email)

            # Auto-link this social provider to existing user
            AuthProvider.objects.create(
                user=user,
                provider=social_user.provider,
                provider_user_id=social_user.provider_user_id,
                email=social_user.email
            )

            return user

        except User.DoesNotExist:
            pass

    # Case 3: No match → registration required
    return None

def generate_reset_token():
    return secrets.token_urlsafe(32)

def create_password_reset_token(user):
    token = generate_reset_token()
    expires_at = timezone.now() + timedelta(minutes=15)

    return PasswordResetToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )

def get_tokens_for_user(user, remember_me=False):
    refresh = RefreshToken.for_user(user)

    if remember_me:
        refresh.set_exp(lifetime=timedelta(days=30))
    else:
        refresh.set_exp(lifetime=timedelta(days=7))

    return str(refresh.access_token), str(refresh)

def anonymize_user(user):
    user.email = f"deleted_{user.id}@example.com"
    user.phone = None
    user.full_name = "Deleted User"
    user.profile_photo = None

    user.is_active = False
    user.state = UserState.DELETED

    user.save()

def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }

def get_object_or_404(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise ValidationError(f"{model.__name__} not found")