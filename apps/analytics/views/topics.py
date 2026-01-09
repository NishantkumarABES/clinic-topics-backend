from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.topics.models import Topic
from core.permissions import IsAdmin


class TopicsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_topics = Topic.objects.count()
        published_topics = Topic.objects.filter(publish_status=True).count()
        unpublished_topics = total_topics - published_topics

        data = {
            "total_topics": total_topics,
            "published_topics": published_topics,
            "unpublished_topics": unpublished_topics,
            "success": True
        }
        return Response(data)
