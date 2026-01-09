from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.CIMS.models import CIMS
from apps.CIMS.serializers import CIMSReadSerializer, CIMSWriteSerializer, AdminCIMSListPagination


class AdminCIMSListCreateAPIView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = AdminCIMSListPagination 

    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")

        queryset = CIMS.objects.all()

        if search:
            queryset = queryset.filter(
                Q(drug_name_generic__icontains=search) |
                Q(drug_class__icontains=search) |
                Q(therapeutic_category__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = CIMSReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    def post(self, request):
        serializer = CIMSWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cims = serializer.save()

        return Response(
            {
                "success": True,
                "data": CIMSReadSerializer(cims).data
            },
            status=status.HTTP_201_CREATED
        )

class AdminCIMSUpdateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, cims_id):
        cims = get_object_or_404(CIMS, id=cims_id)

        serializer = CIMSWriteSerializer(
            cims,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        cims = serializer.save()

        return Response(
            {
                "success": True,
                "data": CIMSReadSerializer(cims).data
            },
            status=status.HTTP_200_OK
        )
