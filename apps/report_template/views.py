from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema

from apps.second_opinion.models import SecondOpinionDoctorRequest
from apps.report_template.models import ReportTemplate
from apps.report_template.serializers import (
    ReportTemplateSerializer, ReportTemplateResponseSerializer
)
from apps.report_template.services import ReportPDFService, calculate_age
from core.permissions import IsDoctor
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401, FORBIDDEN_403

class ReportTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, user):
        try:
            return ReportTemplate.objects.get(doctor=user)
        except ReportTemplate.DoesNotExist:
            return None

    # GET template
    @swagger_auto_schema(
        operation_summary="Get doctor's report template",
        operation_description="Retrieve the report template for the authenticated doctor.",
        tags=["Report Template"],
        responses={
            200: ReportTemplateResponseSerializer,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request):
        template = self.get_object(request.user)
        if not template:
            return Response(
                {
                    "detail": "Report template not created yet.",
                    "data": {"template": None},
                    "success": False,
                },
            )
        serializer = ReportTemplateSerializer(template)
        return Response(
            {
                "detail": "Report template retrieved successfully.",
                "data": serializer.data,
                "success": True,
            }
        )

    # POST create template
    @swagger_auto_schema(
        operation_summary="Create report template",
        operation_description="Create a new report template for the authenticated doctor.",
        tags=["Report Template"],
        request_body=ReportTemplateSerializer,
        responses={
            201: ReportTemplateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        existing = self.get_object(request.user)
        if existing:
            return Response(
                {
                    "detail": "Template already exists. Use PATCH to update.",
                    "data": None,
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReportTemplateSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None,"success": False}
            )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": "Template created successfully.",
                "data": serializer.data,
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )

    # PATCH update template
    @swagger_auto_schema(
        operation_summary="Update report template",
        operation_description="Update the report template for the authenticated doctor.",
        tags=["Report Template"],
        request_body=ReportTemplateSerializer,
        responses={
            200: ReportTemplateResponseSerializer,
            400: BAD_REQUEST_400,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        },
    )
    def patch(self, request):
        template = self.get_object(request.user)
        if not template:
            return Response(
                {
                    "detail": "Template not found. Create it first.",
                    "data": None,
                    "success": False,
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReportTemplateSerializer(
            template,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": "Template updated successfully.", 
                "data": serializer.data,
                "success": True,
            }
        )

class GenerateSecondOpinionReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Generate second opinion report PDF",
        tags=["Report Template"],
        responses={
            200: "PDF file download",
            400: BAD_REQUEST_400,
            403: FORBIDDEN_403,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.select_related(
                "doctor", "doctor__doctor_profile",
                "second_opinion_request",
                "second_opinion_request__patient",
                "second_opinion_request__patient__patient_profile"
            ).get(
                id=doctor_request_id,
                status="completed"
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Completed report not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        patient = doctor_request.second_opinion_request.patient
        doctor = doctor_request.doctor

        # ---- Step 2: Authorization check ----
        if request.user != doctor and request.user != patient:
            return Response(
                {"detail": "You are not allowed to access this report", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        # ---- Step 3: Fetch doctor's report template ----
        try:
            template = ReportTemplate.objects.get(doctor=doctor)
        except ReportTemplate.DoesNotExist:
            return Response(
                {"detail": "Doctor report template not configured", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---- Step 4: Doctor response JSON ----
        response_json = doctor_request.response or {}

        # ---- Step 5: Build patient info (future-proof) ----
        patient_profile = getattr(patient, "patient_profile", None)
        patient_blood_group = getattr(patient_profile, "blood_group", "N/A")
        patient_age = calculate_age(patient.date_of_birth) or "N/A"
        patient_gender = patient.gender or "N/A"


        # ---- Step 6: Build doctor info (future-proof) ----
        doctor_profile = getattr(doctor, "doctor_profile", None)
        doctor_qualification = getattr(doctor_profile, "qualification", "")
        doctor_specialization = getattr(doctor_profile, "specialization", "")

        # ---- Step 7: Build template_data ----
        template_data = {
            # Report header
            "report_title": "Second Opinion Report",
            "report_date": doctor_request.responded_at.strftime("%B %d, %Y"),

            # Clinic branding
            "clinic_logo_url": template.clinic_logo.url if template.clinic_logo else "",
            "clinic_name": template.clinic_name,
            "clinic_address": template.address,
            "clinic_phone": template.phone_number,
            "clinic_email": template.email,
            "clinic_website": template.website or "",

            # Patient details
            "patient_name": patient.full_name,
            "patient_id": str(patient.id),
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_email": patient.email,
            "patient_phone": patient.phone,
            "patient_blood_group": patient_blood_group,

            # Doctor details
            "doctor_name": doctor.full_name,
            "doctor_qualification": doctor_qualification,
            "doctor_specialization": doctor_specialization,

            # Medical content
            "findings": response_json.get("findings", ""),
            "observations": response_json.get("observations", ""),
            "medical_opinion": response_json.get("medical_opinion", ""),
            "patient_questions_responses": response_json.get("answer_to_patient", ""),

            # Signature
            "doctor_signature_url": template.doctor_signature.url if template.doctor_signature else "",
        }

        # ---- Step 8: Generate PDF and get URL ----
        try:
            pdf_url = ReportPDFService.generate_pdf(template_data)
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
            )
        
        # ---- Step 9: Return PDF URL ----
        return Response(
            {
                "detail": "Report generated successfully.",
                "data": {"pdf_url": pdf_url},
                "success": True,
            },
            status=status.HTTP_200_OK
        )