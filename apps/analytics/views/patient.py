from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q
from apps.accounts.constants import UserRole, UserState
from apps.accounts.models import User
from core.permissions import IsAdmin


class PatientAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        stats = User.objects.filter(role=UserRole.PATIENT).aggregate(
            total_patients=Count("id"),
            created_patients=Count("id", filter=Q(state=UserState.CREATED)),
            active_patients=Count("id", filter=Q(state=UserState.ACTIVE)),
            inactive_patients=Count("id", filter=Q(state=UserState.INACTIVE)),
            deleted_patients=Count("id", filter=Q(state=UserState.DELETED)),
        )
        return Response(stats)