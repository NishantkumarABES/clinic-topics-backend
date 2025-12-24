import os, random, secrets, http.client, json
from django.utils import timezone
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from datetime import timedelta
from apps.accounts.constants import UserState, UserRole
from apps.profiles.constants import DoctorVerificationStatus
from apps.accounts.models import User, AuthProvider, PhoneOTP, PasswordResetToken, EmailOTP
from config.settings.base import OTP_EXPIRY_MINUTES

def assert_identity_available(email=None, phone=None):
    qs = User.objects.exclude(state=UserState.DELETED)

    if email and qs.filter(email=email).exists():
        raise ValidationError("Email already linked to another account")

    if phone and qs.filter(phone=phone).exists():
        raise ValidationError("Phone already linked to another account")

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
        if (
            hasattr(user, "doctor_profile") and
            user.doctor_profile.verification_status
            == DoctorVerificationStatus.APPROVED
        ):
            user.state = UserState.ACTIVE
            user.save(update_fields=["state"])

    return user

def generate_otp():
    return f"{random.randint(1000, 9999)}"

def send_phone_otp(phone: str, otp: str) -> dict:
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    PhoneOTP.objects.create(
        phone=phone,
        otp=otp,
        expires_at=expires_at
    )
    print(f"[OTP DEBUG] {phone} -> {otp}")
    authkey = os.environ.get("MSG91_OTP_AUTH_KEY")
    if not authkey:
        raise ValueError("MSG91_OTP_AUTH_KEY is not set in environment variables")

    if not phone or not otp:
        raise ValueError("Phone and OTP are required")
    
    phone = phone.strip().lstrip('+91')
    conn = http.client.HTTPSConnection("api.msg91.com")

    payload = {
        "mobile": f"91{phone}",
        "authkey": authkey,
        "sender": "AESSDW",      
        "otp": otp,
        "message": f"Your Clinic Topics verification code is {otp}. Valid for 5 minutes."
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        conn.request("POST", "/api/v5/otp", body=json.dumps(payload), headers=headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        conn.close()
        result = json.loads(data)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

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

def resolve_social_user(social_user, role=None):
    # 1. Match provider + provider_user_id
    try:
        auth = AuthProvider.objects.select_related("user").get(
            provider=social_user.provider,
            provider_user_id=social_user.provider_user_id
        )
        return auth.user, False
    except AuthProvider.DoesNotExist:
        pass

    # 2. Match email (if provided)
    user = None
    if social_user.email:
        try:
            user = User.objects.get(email=social_user.email)
        except User.DoesNotExist:
            pass

    # 3. Create user if not found
    if not user:
        user = User.objects.create(
            email=social_user.email,
            role=role or UserRole.PATIENT,
            state=UserState.CREATED
        )

    # 4. Link provider
    AuthProvider.objects.create(
        user=user,
        provider=social_user.provider,
        provider_user_id=social_user.provider_user_id,
        email=social_user.email
    )

    return user, True

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