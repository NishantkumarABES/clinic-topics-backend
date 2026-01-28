from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.accounts.constants import UserState


@shared_task
def mark_inactive_users():
    """
    Mark users as INACTIVE if they have not logged in for 6 months.
    """

    cutoff_date = timezone.now() - timedelta(days=180)

    inactive_users = User.objects.filter(
        last_login__lt=cutoff_date,
        state__in=[UserState.ACTIVE, UserState.CREATED]
    )

    count = inactive_users.update(state=UserState.INACTIVE)

    return f"{count} users marked inactive"
