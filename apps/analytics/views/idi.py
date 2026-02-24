from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.IDI.models import IDI
from apps.IDI.constants import IDIStatus
from core.permissions import IsAdmin


class IDIAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_idi = IDI.objects.count()
        published_idi = IDI.objects.filter(status=IDIStatus.PUBLISHED).count()
        draft_idi = total_idi - published_idi
        

        data = {
            "total_idi": total_idi,
            "published_idi": published_idi,
            "draft_idi": draft_idi
        }
        return Response(data)
