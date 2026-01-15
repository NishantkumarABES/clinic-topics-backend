from django.db.models import Q, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.accounts.constants import UserRole
from apps.profiles.models import DoctorProfile
from apps.appointments.serializers import DoctorListSerializer, DoctorDetailSerializer


class DoctorListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class DoctorListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = DoctorListPagination

    def get(self, request):
        # Only patients allowed
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can view doctors"},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = DoctorProfile.objects.select_related("user").all()

        # ---------- Filters ----------
        specialization = request.query_params.get("specialization")
        min_experience = request.query_params.get("min_experience")
        max_fee = request.query_params.get("max_fee")
        min_rating = request.query_params.get("min_rating")
        search = request.query_params.get("search")

        if specialization:
            queryset = queryset.filter(
                specialization__icontains=specialization
            )

        if min_experience:
            queryset = queryset.filter(
                years_of_experience__gte=int(min_experience)
            )

        if max_fee:
            queryset = queryset.filter(
                consultation_fee__lte=max_fee
            )

        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search) |
                Q(clinic_name__icontains=search)
            )

        # Rating filter (requires annotation)
        if min_rating:
            queryset = queryset.annotate(
                avg_rating=Avg("user__ratings_received__rating")
            ).filter(avg_rating__gte=float(min_rating))

        queryset = queryset.order_by("-created_at")

        # ---------- Pagination ----------
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = DoctorListSerializer(page, many=True)

        return paginator.get_paginated_response({
            "doctors": serializer.data,
            "success": True
        })

class DoctorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doctor_id):
        if request.user.role != UserRole.PATIENT:
            return Response(
                {"detail": "Only patients can view doctor details"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            doctor_profile = DoctorProfile.objects.select_related("user").get(
                user__id=doctor_id
            )
        except DoctorProfile.DoesNotExist:
            return Response(
                {"detail": "Doctor not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorDetailSerializer(doctor_profile)

        return Response({
            "doctor": serializer.data,
            "success": True
        })
