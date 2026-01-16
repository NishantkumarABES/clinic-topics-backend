from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from apps.cms.models import StaticPageVersion, StaticPage, ContactUsSubmission, SiteConfiguration


class StaticPageVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticPageVersion
        fields = (
            "version",
            "title",
            "content",
            "created_at",
        )


class AdminStaticPageUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    content = serializers.CharField()

    def create(self, validated_data):
        page: StaticPage = self.context["page"]
        user = self.context["request"].user

        last_version = (
            StaticPageVersion.objects
            .filter(page=page)
            .order_by("-version")
            .first()
        )

        next_version = (last_version.version + 1) if last_version else 1

        # Use existing title if not provided
        title = validated_data.get("title")
        if not title and last_version:
            title = last_version.title
        elif not title:
            title = page.get_page_type_display()

        version = StaticPageVersion.objects.create(
            page=page,
            version=next_version,
            title=title,
            content=validated_data["content"],
            created_by=user,
            is_published=True  # Auto-publish for admin updates
        )

        # Unpublish other versions
        StaticPageVersion.objects.filter(
            page=page
        ).exclude(id=version.id).update(is_published=False)

        return version


class ContactUsSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUsSubmission
        fields = (
            "name",
            "phone_number",
            "email",
            "message",
        )


# ========== ADMIN SERIALIZERS ==========

class AdminSettingSerializer(serializers.Serializer):
    """Serializer for admin settings list/detail view."""
    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    content = serializers.CharField()
    updatedAt = serializers.DateTimeField()
    updatedBy = serializers.CharField(allow_null=True)
    version = serializers.IntegerField()


class AdminSettingVersionSerializer(serializers.ModelSerializer):
    """Serializer for version history."""
    updatedBy = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = StaticPageVersion
        fields = (
            "id",
            "version",
            "title",
            "content",
            "is_published",
            "updatedAt",
            "updatedBy",
        )

    def get_updatedBy(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return None


class ContactSubmissionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminContactSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for admin contact submissions list."""

    class Meta:
        model = ContactUsSubmission
        fields = (
            "id",
            "name",
            "phone_number",
            "email",
            "message",
            "is_resolved",
            "created_at",
        )


class SiteConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for site-wide configuration settings."""

    class Meta:
        model = SiteConfiguration
        fields = (
            "id",
            "ad_interval",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
