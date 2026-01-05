from rest_framework import serializers
from apps.cms.models import StaticPageVersion, StaticPage, ContactUsSubmission


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
    title = serializers.CharField(max_length=255)
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

        return StaticPageVersion.objects.create(
            page=page,
            version=next_version,
            title=validated_data["title"],
            content=validated_data["content"],
            created_by=user,
            is_published=False
        )



class ContactUsSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUsSubmission
        fields = (
            "name",
            "phone_number",
            "email",
            "message",
        )
