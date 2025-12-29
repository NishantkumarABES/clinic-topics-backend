from rest_framework.views import APIView
from rest_framework.response import Response
from apps.accounts.models import User
from core.permissions import IsAdmin


class PatientAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]
    def get(self, request):
        total_patients = User.objects.filter(role="patient").count()
        active_patients = User.objects.filter(role="patient", is_active=True).count()
        inactive_patients = total_patients - active_patients
        data = {
            "total_patients": total_patients,
            "active_patients": active_patients,
            "inactive_patients": inactive_patients,
        }
        return Response(data)