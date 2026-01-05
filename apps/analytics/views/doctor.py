from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from core.permissions import IsAdmin


class DoctorAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_doctors = User.objects.filter(role=UserRole.DOCTOR).count()
        active_doctors = User.objects.filter(role=UserRole.DOCTOR, is_active=True).count()
        inactive_doctors = total_doctors - active_doctors

        data = {
            "total_doctors": total_doctors,
            "active_doctors": active_doctors,
            "inactive_doctors": inactive_doctors,
            "success": True
        }
        return Response(data)
