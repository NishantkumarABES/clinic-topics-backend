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
from apps.report_template.services import ReportPDFService
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
                {"detail": "Report template not created yet."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ReportTemplateSerializer(template)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST create template
    @swagger_auto_schema(request_body=ReportTemplateSerializer)
    def post(self, request):
        existing = self.get_object(request.user)
        if existing:
            return Response(
                {"detail": "Template already exists. Use PATCH to update."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReportTemplateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # PATCH update template
    @swagger_auto_schema(request_body=ReportTemplateSerializer)
    def patch(self, request):
        template = self.get_object(request.user)
        if not template:
            return Response(
                {"detail": "Template not found. Create it first."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReportTemplateSerializer(
            template,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GenerateSecondOpinionReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: "PDF report generated successfully",
            404: "Completed report not found",
            400: "Doctor report template not configured",
        },
        operation_id="generate_second_opinion_report",
    )
    def get(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.select_related(
                "second_opinion_request__patient", "doctor"
            ).get(
                id=doctor_request_id,
                doctor=request.user,
                status="completed"
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Completed report not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Fetch doctor's report template
        try:
            template = ReportTemplate.objects.get(doctor=request.user)
        except ReportTemplate.DoesNotExist:
            return Response(
                {"detail": "Doctor report template not configured"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Doctor response JSON
        response_json = doctor_request.response or {}

        # 4. Build template_data dictionary
        template_data = {
            "report_title": "Second Opinion Report",
            "report_date": doctor_request.responded_at.strftime("%B %d, %Y"),

            "clinic_logo_url": template.clinic_logo.url if template.clinic_logo else "",
            "clinic_name": template.clinic_name,
            "clinic_address": template.address,
            "clinic_phone": template.phone_number,
            "clinic_email": template.email,
            "clinic_website": template.website or "",

            "patient_name": doctor_request.second_opinion_request.patient.full_name,
            "patient_id": str(doctor_request.second_opinion_request.patient.id),
            "patient_age": getattr(doctor_request.second_opinion_request.patient, "age", "N/A"),
            "patient_gender": getattr(doctor_request.second_opinion_request.patient, "gender", "N/A"),
            "patient_contact": doctor_request.second_opinion_request.patient.email,

            "findings": response_json.get("findings", ""),
            "observations": response_json.get("observations", ""),
            "medical_opinion": response_json.get("medical_opinion", ""),
            "patient_questions_responses": response_json.get("answer_to_patient", ""),

            "doctor_signature_url": template.doctor_signature.url if template.doctor_signature else "",
            "doctor_name": request.user.full_name,
            "doctor_credentials": getattr(request.user.doctor_profile, "qualification", "")
        }

        # 5. Generate PDF
        pdf_path = ReportPDFService.generate_pdf(template_data)

        # 6. Return PDF file
        return FileResponse(
            open(pdf_path, "rb"),
            content_type="application/pdf",
            filename=os.path.basename(pdf_path)
        )