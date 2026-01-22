from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from apps.IDI.models import IDI
from apps.IDI.serializers import IDIReadSerializer, IDIWriteSerializer, AdminIDIListPagination


class AdminIDIListCreateAPIView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = AdminIDIListPagination 

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")
        therapeutic_category_filter = request.query_params.get("therapeutic_category")
        drug_class_filter = request.query_params.get("drug_class")

        queryset = IDI.objects.all()

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

        serializer = IDIReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = IDIWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idi = serializer.save()

        return Response(
            {
                "success": True,
                "data": IDIReadSerializer(idi).data
            },
            status=status.HTTP_201_CREATED
        )

class AdminIDIUpdateAPIView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, idi_id):
        idi = get_object_or_404(IDI, id=idi_id)

        serializer = IDIWriteSerializer(
            idi,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        idi = serializer.save()

        return Response(
            {
                "success": True,
                "data": IDIReadSerializer(idi).data
            },
            status=status.HTTP_200_OK
        )


class IDIListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = AdminIDIListPagination

    @swagger_auto_schema(
        responses={200: IDIReadSerializer(many=True)}
    )
    def get(self, request):
        search = request.query_params.get("search")

        # Only return published drugs for regular users
        queryset = IDI.objects.filter(status="published")

        if search:
            queryset = queryset.filter(
                Q(drug_name_generic__icontains=search) |
                Q(drug_class__icontains=search) |
                Q(therapeutic_category__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = IDIReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

class IDIDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: IDIReadSerializer()}
    )   
    def get(self, request, idi_id):
        # Only allow access to published drugs
        idi = get_object_or_404(IDI, id=idi_id, status="published")

        serializer = IDIReadSerializer(idi)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
