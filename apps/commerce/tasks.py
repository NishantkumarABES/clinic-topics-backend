from celery import shared_task
from django.utils import timezone
from apps.commerce.models import Coupon


@shared_task
def deactivate_expired_coupons():
    now = timezone.now()

    expired_coupons = Coupon.objects.filter(
        is_active=True,
        valid_until__lt=now
    )

    count = expired_coupons.update(is_active=False)

    return f"{count} coupons deactivated"