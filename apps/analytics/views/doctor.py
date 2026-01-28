from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q
from apps.accounts.models import User
from apps.accounts.constants import UserRole, UserState
from core.permissions import IsAdmin


class DoctorAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        stats = User.objects.filter(role=UserRole.DOCTOR).aggregate(
            total_doctors=Count("id"),
            created_doctors=Count("id", filter=Q(state=UserState.CREATED)),
            active_doctors=Count("id", filter=Q(state=UserState.ACTIVE)),
            inactive_doctors=Count("id", filter=Q(state=UserState.INACTIVE)),
            deleted_doctors=Count("id", filter=Q(state=UserState.DELETED)),
        )
        return Response(stats)
        
