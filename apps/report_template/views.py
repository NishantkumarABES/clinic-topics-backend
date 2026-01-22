import os
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import FileResponse
from drf_yasg.utils import swagger_auto_schema

from apps.second_opinion.models import SecondOpinionDoctorRequest
from apps.report_template.models import ReportTemplate
from apps.report_template.serializers import ReportTemplateSerializer
from apps.report_template.services import ReportPDFService, calculate_age
from core.permissions import IsDoctor

class ReportTemplateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, user):
        try:
            return ReportTemplate.objects.get(doctor=user)
        except ReportTemplate.DoesNotExist:
            return None

    # GET template
    def get(self, request):
        template = self.get_object(request.user)
        if not template:
            return Response(
                {
                    "detail": "Report template not created yet.",
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
    @swagger_auto_schema(request_body=ReportTemplateSerializer)
    def post(self, request):
        existing = self.get_object(request.user)
        if existing:
            return Response(
                {
                    "detail": "Template already exists. Use PATCH to update.",
                    "success": False,
                },
            )

        serializer = ReportTemplateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Template created successfully.",
                    "data": serializer.data,
                    "success": True,
                }
            )

        return Response(serializer.errors)

    # PATCH update template
    @swagger_auto_schema(request_body=ReportTemplateSerializer)
    def patch(self, request):
        template = self.get_object(request.user)
        if not template:
            return Response(
                {
                    "detail": "Template not found. Create it first.",
                    "success": False,
                },
            )

        serializer = ReportTemplateSerializer(
            template,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "detail": "Template updated successfully.", 
                    "data": serializer.data,
                    "success": True,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GenerateSecondOpinionReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
                {"detail": "Completed report not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        patient = doctor_request.second_opinion_request.patient
        doctor = doctor_request.doctor

        # ---- Step 2: Authorization check ----
        if request.user != doctor and request.user != patient:
            return Response(
                {"detail": "You are not allowed to access this report"},
                status=status.HTTP_403_FORBIDDEN
            )

        # ---- Step 3: Fetch doctor's report template ----
        try:
            template = ReportTemplate.objects.get(doctor=doctor)
        except ReportTemplate.DoesNotExist:
            return Response(
                {"detail": "Doctor report template not configured"},
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

        # ---- Step 8: Generate PDF ----
        pdf_path = ReportPDFService.generate_pdf(template_data)

        # ---- Step 9: Return file ----
        response = FileResponse(
            open(pdf_path, "rb"),
            content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'inline; filename="{os.path.basename(pdf_path)}"'
        )
        return response