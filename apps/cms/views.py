from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from apps.cms.models import StaticPage, StaticPageVersion
from apps.cms.serializers import StaticPageVersionSerializer, AdminStaticPageUpdateSerializer, ContactUsSubmissionSerializer
from apps.cms.services import publish_version
from core.permissions import IsAdmin

class StaticPageView(APIView):
    permission_classes = []

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, page_type):
        try:
            page = StaticPage.objects.get(
                page_type=page_type,
                is_active=True
            )
            version = StaticPageVersion.objects.get(
                page=page,
                is_published=True
            )
        except (StaticPage.DoesNotExist, StaticPageVersion.DoesNotExist):
            return Response(
                {"detail": "Page not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StaticPageVersionSerializer(version)
        return Response(serializer.data)

class AdminStaticPageUpdateView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, page_type):
        try:
            page = StaticPage.objects.get(page_type=page_type, is_active=True)
        except StaticPage.DoesNotExist:
            return Response(
                {"detail": "Invalid page type"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AdminStaticPageUpdateSerializer(
            data=request.data,
            context={"page": page, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        version = serializer.save()

        return Response(
            {
                "message": "Draft version created",
                "version": version.version,
                "id": str(version.id)
            },
            status=status.HTTP_201_CREATED
        )

class AdminPublishStaticPageView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, version_id):
        try:
            version = StaticPageVersion.objects.get(id=version_id)
        except StaticPageVersion.DoesNotExist:
            return Response(
                {"detail": "Version not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        publish_version(version)

        return Response(
            {"message": f"Version {version.version} published"},
            status=status.HTTP_200_OK
        )

class ContactUsSubmitView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = ContactUsSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Your message has been submitted successfully"},
            status=status.HTTP_201_CREATED
        )