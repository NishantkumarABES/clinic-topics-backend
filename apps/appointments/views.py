from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.profiles.models import DoctorProfile
from apps.appointments.serializers import DoctorListSerializer, DoctorDetailSerializer

class DoctorListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = DoctorProfile.objects.filter(
            verification_status="approved",
            user__state="active"
        )

        name = request.query_params.get("name")
        specialization = request.query_params.get("specialization")
        clinic = request.query_params.get("clinic")
        language = request.query_params.get("language")
        min_fee = request.query_params.get("min_fee")
        max_fee = request.query_params.get("max_fee")

        if name:
            qs = qs.filter(user__full_name__icontains=name)

        if specialization:
            qs = qs.filter(specializations__icontains=specialization)

        if clinic:
            qs = qs.filter(clinic_name__icontains=clinic)

        if language:
            qs = qs.filter(languages_spoken__icontains=language)

        if min_fee:
            qs = qs.filter(consultation_fee__gte=min_fee)

        if max_fee:
            qs = qs.filter(consultation_fee__lte=max_fee)

        serializer = DoctorListSerializer(qs, many=True)
        return Response(serializer.data)

class DoctorDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
        try:
            doctor = DoctorProfile.objects.get(
                id=doctor_id,
                verification_status="approved"
            )
        except DoctorProfile.DoesNotExist:
            return Response({"detail": "Doctor not found"}, status=404)

        serializer = DoctorDetailSerializer(doctor)
        return Response(serializer.data)
