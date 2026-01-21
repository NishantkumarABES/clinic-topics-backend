from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema

from apps.report_template.models import ReportTemplate
from apps.report_template.serializers import ReportTemplateSerializer
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
