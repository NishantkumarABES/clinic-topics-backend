from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.constants import UserRole
from apps.accounts.models import User
from core.permissions import IsAdmin


class PatientAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_patients = User.objects.filter(role=UserRole.PATIENT).count()
        active_patients = User.objects.filter(role=UserRole.PATIENT, is_active=True).count()
        inactive_patients = total_patients - active_patients
        data = {
            "total_patients": total_patients,
            "active_patients": active_patients,
            "inactive_patients": inactive_patients,
        }
        return Response(data)