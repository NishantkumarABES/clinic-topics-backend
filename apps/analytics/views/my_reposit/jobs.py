from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.jobs.models import JobPost
from apps.jobs.constants import JobPostStatus
from core.permissions import IsAdmin


class JobsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_jobs = JobPost.objects.count()
        draft_jobs = JobPost.objects.filter(status=JobPostStatus.DRAFT).count()
        published_jobs = JobPost.objects.filter(status=JobPostStatus.PUBLISHED).count()
        rejected_jobs = JobPost.objects.filter(status=JobPostStatus.REJECTED).count()
        in_review_jobs = JobPost.objects.filter(status=JobPostStatus.IN_REVIEW).count()
        closed_jobs = JobPost.objects.filter(status=JobPostStatus.CLOSED).count()
        expired_jobs = JobPost.objects.filter(status=JobPostStatus.EXPIRED).count()

        data = {
            "total_jobs": total_jobs,
            "draft_jobs": draft_jobs,
            "published_jobs": published_jobs,
            "rejected_jobs": rejected_jobs,
            "in_review_jobs": in_review_jobs,
            "closed_jobs": closed_jobs,
            "expired_jobs": expired_jobs,
        }
        return Response(data)
