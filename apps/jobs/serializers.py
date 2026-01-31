from django.utils import timezone
from rest_framework import serializers

from apps.jobs.models import JobPost
from apps.jobs.constants import JobStatus, ApplyMethod


class JobPostCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobPost
        exclude = (
            "created_by",
            "status",
            "created_at",
            "updated_at",
            "agreed_at",
        )

    def validate(self, attrs):
        """
        Cross-field validation.
        """
        apply_method = attrs.get("apply_method")
        apply_target = attrs.get("apply_target")
        agreed = attrs.get("agreed_to_terms")

        if apply_method in (
            ApplyMethod.EXTERNAL_LINK,
            ApplyMethod.EMAIL,
        ) and not apply_target:
            raise serializers.ValidationError(
                {
                    "apply_target": (
                        "This field is required when apply method is "
                        "external link or email."
                    )
                }
            )

        if not agreed:
            raise serializers.ValidationError(
                {
                    "agreed_to_terms": (
                        "You must confirm permission to post this job."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        """
        Attach creator and agreement timestamp.
        """
        user = self.context["request"].user

        validated_data["created_by"] = user
        validated_data["agreed_at"] = timezone.now()
        validated_data["status"] = JobStatus.PENDING_REVIEW

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Preserve agreed_at once set.
        """
        if instance.agreed_at is None and validated_data.get("agreed_to_terms"):
            validated_data["agreed_at"] = timezone.now()

        return super().update(instance, validated_data)

class JobPostListDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()

    class Meta:
        model = JobPost
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "status",
            "created_at",
            "updated_at",
            "agreed_at",
        )
