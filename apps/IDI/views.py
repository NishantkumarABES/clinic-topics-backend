from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from apps.IDI.models import IDI
from apps.IDI.serializers import (
    IDIReadSerializer, IDIWriteSerializer, AdminIDIListPagination,
    IDIDataResponseSerializer, IDIListDataSerializer, ExtractIDIRequestSerializer
)
from core.api_responses import NOT_FOUND_404
from apps.IDI.services import IDIExtractionService



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
        return Response(response.data)

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = IDIWriteSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        idi = serializer.save()

        return Response(
            {
                "detail": "IDI created successfully",
                "data": IDIReadSerializer(idi).data,
                "success": True
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
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        idi = serializer.save()

        return Response(
            {
                "detail": "IDI updated successfully",
                "data": IDIReadSerializer(idi).data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

class IDIListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = AdminIDIListPagination

    @swagger_auto_schema(
        operation_description="Get list of published IDI drugs",
        responses={
            200: IDIListDataSerializer,
        }
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
        return Response(
            {
                "detail" : "IDI list retrieved successfully",
                "data" : response.data,
                "success" : True
            }
        )

class IDIDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get details of a specific published IDI drug",
        responses={
            200: IDIDataResponseSerializer,
            404: NOT_FOUND_404,
        }
    )   
    def get(self, request, idi_id):
        # Only allow access to published drugs
        idi = get_object_or_404(IDI, id=idi_id, status="published")

        serializer = IDIReadSerializer(idi)
        return Response(
            {
                "detail": "IDI retrieved successfully",
                "data": serializer.data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

class AdminIDIExtractAPIView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Extract structured IDI from paragraph",
        request_body=ExtractIDIRequestSerializer,
        responses={200: IDIDataResponseSerializer},
        auto_schema=None
    )
    def post(self, request):
        serializer = ExtractIDIRequestSerializer(data=request.data)

        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        paragraph = serializer.validated_data["paragraph"]
        extractor = IDIExtractionService()
        extracted_data = extractor.extract(paragraph)

        # 🔥 MOCK DATA — Replace later with LLM extraction
        mock_data = {
            "drug_name_generic": "Metformin",
            "drug_class": "Biguanide",
            "therapeutic_category": "Antidiabetic",
            "brands_in_india": "Glycomet, Obimet",
            "strengths_available": "250mg, 500mg, 850mg, 1000mg",
            "formulations_routes": "Oral tablets",
            "core_clinical_role": "First-line therapy for Type 2 Diabetes",
            "preferred_clinical_scenarios": "Overweight patients with insulin resistance",
            "where_benefit_limited": "Severe renal impairment",
            "usual_adult_dose": "500mg twice daily",
            "timing_relative_to_meals": "Take with meals",
            "review_duration_plan": "Review after 3 months",
            "common_adverse_effects": "GI upset, nausea, diarrhea",
            "serious_but_uncommon_risks": "Lactic acidosis",
            "long_term_therapy_cautions": "Monitor B12 levels",
            "guidelines": "ADA recommends as first-line agent",
            "landmark_trials": "UKPDS trial",
            "status": "draft",
            "key_interactions": [
                {
                    "interaction_title": "Alcohol",
                    "clinical_impact": "Increases risk of lactic acidosis",
                    "what_to_do": "Avoid excessive alcohol"
                }
            ],
            "practical_prescribing_pearls": [
                {
                    "pearl_title": "Start low",
                    "pearl_content": "Begin with low dose to reduce GI effects"
                }
            ],
        }

        return Response(
            {
                "detail": "IDI extracted successfully",
                "data": extracted_data,
                "success": True
            },
            status=status.HTTP_200_OK
        )
