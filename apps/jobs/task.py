from celery import shared_task
from django.utils import timezone
from .models import JobPost, JobPostStatus

@shared_task
def mark_expired_job_posts():
    today = timezone.now().date()

    expired_jobs = JobPost.objects.filter(
        status=JobPostStatus.PUBLISHED,
        application_deadline__lt=today
    )

    updated_count = expired_jobs.update(status=JobPostStatus.EXPIRED)

    return f"{updated_count} jobs marked as expired"