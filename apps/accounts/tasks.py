from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from apps.accounts.models import User, PhoneOTP, EmailOTP
from apps.accounts.constants import UserState


@shared_task
def mark_inactive_users():
    cutoff_date = timezone.now() - timedelta(days=180)

    inactive_users = User.objects.filter(
        state__in=[UserState.ACTIVE, UserState.CREATED]
    ).filter(
        Q(last_login__lt=cutoff_date) |
        Q(last_login__isnull=True, created_at__lt=cutoff_date)
    )

    count = inactive_users.update(state=UserState.INACTIVE)

    return f"{count} users marked inactive"

@shared_task
def cleanup_expired_otps():
    now = timezone.now()

    phone_deleted, _ = PhoneOTP.objects.filter(
        Q(is_used=True) | Q(expires_at__lt=now)
    ).delete()

    email_deleted, _ = EmailOTP.objects.filter(
        Q(is_used=True) | Q(expires_at__lt=now)
    ).delete()

    return {
        "phone_otps_deleted": phone_deleted,
        "email_otps_deleted": email_deleted,
    }