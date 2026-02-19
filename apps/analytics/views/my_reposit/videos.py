from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.videos.models import Video
from apps.articles.constants import Status
from core.permissions import IsAdmin


class VideosAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_videos = Video.objects.count()
        draft_videos = Video.objects.filter(status=Status.DRAFT).count()
        published_videos = Video.objects.filter(status=Status.PUBLISHED).count()
        rejected_videos = Video.objects.filter(status=Status.REJECTED).count()
        in_review_videos = Video.objects.filter(status=Status.REVIEW).count()
        data = {
            "total_videos": total_videos,
            "draft_videos": draft_videos,
            "published_videos": published_videos,
            "rejected_videos": rejected_videos,
            "in_review_videos": in_review_videos,
        }
        return Response(data)
