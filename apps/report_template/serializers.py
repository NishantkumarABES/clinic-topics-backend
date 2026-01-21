from rest_framework import serializers
from .models import ReportTemplate


class ReportTemplateSerializer(serializers.ModelSerializer):
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
        return ReportTemplate.objects.create(doctor=doctor, **validated_data)

    def update(self, instance, validated_data):
        # Allow partial updates safely
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
