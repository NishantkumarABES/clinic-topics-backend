import base64, uuid
from rest_framework import serializers
from django.core.files.base import ContentFile
from apps.report_template.models import ReportTemplate


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Already a file (multipart upload)
        if hasattr(data, "read"):
            return super().to_internal_value(data)

        # Base64 string
        if isinstance(data, str):
            if "data:image" in data:
                _, data = data.split(";base64,")

            try:
                decoded_file = base64.b64decode(data)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Invalid base64 image")

            file_name = f"{uuid.uuid4()}.png"
            data = ContentFile(decoded_file, name=file_name)

        return super().to_internal_value(data)

class ReportTemplateSerializer(serializers.ModelSerializer):
    doctor_signature = Base64ImageField(
        required=False,
        allow_null=True
    )
    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "clinic_logo",
            "doctor_signature",
            "clinic_name",
            "address",
            "phone_number",
            "website",
            "email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        doctor = self.context["request"].user
        return ReportTemplate.objects.create(
            doctor=doctor,
            **validated_data
        )

    def update(self, instance, validated_data):
        # Allow partial updates safely
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ===================== Response Serializers =====================

class StandardResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False)
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "ReportTemplateStandardResponseSerializer"

class ReportTemplateResponseSerializer(serializers.Serializer):
    """Response serializer for report template endpoints."""
    detail = serializers.CharField()
    data = ReportTemplateSerializer(allow_null=True)
    success = serializers.BooleanField()

    class Meta:
        ref_name = "ReportTemplateResponseSerializer"
