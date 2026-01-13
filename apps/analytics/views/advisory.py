from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.advisory.models import AdvisoryMember
from core.permissions import IsAdmin


class AdvisoryAnalyticsView(APIView):
    """Analytics endpoint for Advisory members metrics."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_members = AdvisoryMember.objects.count()
        active_members = AdvisoryMember.objects.filter(status="active").count()
        inactive_members = AdvisoryMember.objects.filter(status="inactive").count()

        data = {
            "total_members": total_members,
            "active_members": active_members,
            "inactive_members": inactive_members,
            "success": True
        }
        return Response(data)
