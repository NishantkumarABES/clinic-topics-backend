from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema

from apps.cms.models import StaticPage, StaticPageVersion, ContactUsSubmission, PageType, SiteConfiguration
from apps.cms.serializers import (
    StaticPageVersionSerializer, 
    AdminStaticPageUpdateSerializer, 
    ContactUsSubmissionSerializer,
    AdminSettingSerializer,
    AdminSettingVersionSerializer,
    AdminContactSubmissionSerializer,
    ContactSubmissionPagination,
    SiteConfigurationSerializer,
)
from core.permissions import IsAdmin


# ========== PUBLIC VIEWS ==========

class StaticPageView(APIView):
    """Public view to get published static page content."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, page_type):
        try:
            page = StaticPage.objects.get(
                page_type=page_type,
                is_active=True
            )
            version = StaticPageVersion.objects.filter(
                page=page,
                is_published=True
            ).first()
            
            if not version:
                return Response(
                    {"detail": "No published content found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except StaticPage.DoesNotExist:
            return Response(
                {"detail": "Page not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StaticPageVersionSerializer(version)
        return Response(serializer.data)


class ContactUsSubmitView(APIView):
    """Public view to submit contact form."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = ContactUsSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Your message has been submitted successfully"},
            status=status.HTTP_201_CREATED
        )


# ========== ADMIN VIEWS ==========

class AdminSettingsListView(APIView):
    """Admin view to list all settings with their latest published content."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        settings_list = []
        
        # Get all page types
        for page_type_value, page_type_display in PageType.choices:
            # Get or create the static page
            page, _ = StaticPage.objects.get_or_create(
                page_type=page_type_value,
                defaults={"is_active": True}
            )
            
            # Get the latest version (published or most recent)
            version = StaticPageVersion.objects.filter(page=page).first()
            
            if version:
                settings_list.append({
                    "id": str(version.id),
                    "type": page_type_value,
                    "title": version.title,
                    "content": version.content,
                    "updatedAt": version.created_at,
                    "updatedBy": version.created_by.full_name if version.created_by else None,
                    "version": version.version,
                })
            else:
                # No version exists yet
                settings_list.append({
                    "id": str(page.id),
                    "type": page_type_value,
                    "title": page_type_display,
                    "content": "",
                    "updatedAt": None,
                    "updatedBy": None,
                    "version": 0,
                })
        
        return Response(settings_list)


class AdminSettingDetailView(APIView):
    """Admin view to get and update a single setting."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, page_type):
        try:
            page = StaticPage.objects.get(page_type=page_type)
        except StaticPage.DoesNotExist:
            # Create the page if it doesn't exist
            page = StaticPage.objects.create(
                page_type=page_type,
                is_active=True
            )
        
        version = StaticPageVersion.objects.filter(page=page).first()
        
        if version:
            data = {
                "id": str(version.id),
                "type": page_type,
                "title": version.title,
                "content": version.content,
                "updatedAt": version.created_at,
                "updatedBy": version.created_by.full_name if version.created_by else None,
                "version": version.version,
            }
        else:
            data = {
                "id": str(page.id),
                "type": page_type,
                "title": page.get_page_type_display(),
                "content": "",
                "updatedAt": None,
                "updatedBy": None,
                "version": 0,
            }
        
        return Response(data)

    @swagger_auto_schema(auto_schema=None)
    def put(self, request, page_type):
        try:
            page = StaticPage.objects.get(page_type=page_type)
        except StaticPage.DoesNotExist:
            page = StaticPage.objects.create(
                page_type=page_type,
                is_active=True
            )

        serializer = AdminStaticPageUpdateSerializer(
            data=request.data,
            context={"page": page, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        version = serializer.save()

        return Response({
            "id": str(version.id),
            "type": page_type,
            "title": version.title,
            "content": version.content,
            "updatedAt": version.created_at,
            "updatedBy": version.created_by.full_name if version.created_by else None,
            "version": version.version,
        })


class AdminSettingVersionsView(APIView):
    """Admin view to list all versions of a setting."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, page_type):
        try:
            page = StaticPage.objects.get(page_type=page_type)
        except StaticPage.DoesNotExist:
            return Response([])
        
        versions = StaticPageVersion.objects.filter(page=page).order_by("-version")
        serializer = AdminSettingVersionSerializer(versions, many=True)
        return Response(serializer.data)


class AdminPublishVersionView(APIView):
    """Admin view to publish a specific version."""
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

        # Unpublish all other versions
        StaticPageVersion.objects.filter(
            page=version.page
        ).update(is_published=False)
        
        # Publish this version
        version.is_published = True
        version.save(update_fields=["is_published"])

        return Response({
            "message": f"Version {version.version} published",
            "version": version.version
        })


class AdminContactListView(APIView):
    """Admin view to list contact submissions."""
    permission_classes = [IsAdmin]
    pagination_class = ContactSubmissionPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        search = request.query_params.get("search")
        is_resolved = request.query_params.get("is_resolved")
        
        queryset = ContactUsSubmission.objects.all()
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(message__icontains=search)
            )
        
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=(is_resolved.lower() == "true"))
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        
        serializer = AdminContactSubmissionSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response


class AdminContactUpdateView(APIView):
    """Admin view to update contact submission (mark as resolved)."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, contact_id):
        try:
            contact = ContactUsSubmission.objects.get(id=contact_id)
        except ContactUsSubmission.DoesNotExist:
            return Response(
                {"detail": "Contact submission not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        is_resolved = request.data.get("is_resolved")
        if is_resolved is not None:
            contact.is_resolved = is_resolved
            contact.save(update_fields=["is_resolved"])
        
        serializer = AdminContactSubmissionSerializer(contact)
        return Response({
            "success": True,
            "data": serializer.data
        })


class AdminSiteConfigurationView(APIView):
    """Admin view to get and update site configuration."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        config = SiteConfiguration.get_config()
        serializer = SiteConfigurationSerializer(config)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request):
        config = SiteConfiguration.get_config()
        serializer = SiteConfigurationSerializer(
            config,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "success": True,
            "message": "Site configuration updated successfully",
            "data": serializer.data
        })