from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from apps.CIMS.models import CIMS
from apps.CIMS.serializers import CIMSReadSerializer, CIMSWriteSerializer, AdminCIMSListPagination


class AdminCIMSListCreateAPIView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = AdminCIMSListPagination 

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")
        therapeutic_category_filter = request.query_params.get("therapeutic_category")
        drug_class_filter = request.query_params.get("drug_class")

        queryset = CIMS.objects.all()

        if search:
            queryset = queryset.filter(
                Q(drug_name_generic__icontains=search) |
                Q(drug_class__icontains=search) |
                Q(therapeutic_category__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if therapeutic_category_filter:
            queryset = queryset.filter(therapeutic_category=therapeutic_category_filter)

        if drug_class_filter:
            queryset = queryset.filter(drug_class=drug_class_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = CIMSReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    @swagger_auto_schema(auto_schema=None)
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

    @swagger_auto_schema(auto_schema=None)
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


class CIMSListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = AdminCIMSListPagination

    @swagger_auto_schema(
        responses={200: CIMSReadSerializer(many=True)}
    )
    def get(self, request):
        search = request.query_params.get("search")

        # Only return published drugs for regular users
        queryset = CIMS.objects.filter(status="published")

        if search:
            queryset = queryset.filter(
                Q(drug_name_generic__icontains=search) |
                Q(drug_class__icontains=search) |
                Q(therapeutic_category__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = CIMSReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

class CIMSDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: CIMSReadSerializer()}
    )   
    def get(self, request, cims_id):
        # Only allow access to published drugs
        cims = get_object_or_404(CIMS, id=cims_id, status="published")

        serializer = CIMSReadSerializer(cims)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
