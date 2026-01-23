from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from apps.advisory.models import AdvisoryMember


class AdvisoryPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdvisoryMemberReadSerializer(serializers.ModelSerializer):
    """Serializer for reading advisory member data."""
    
    class Meta:
        model = AdvisoryMember
        fields = [
            "id",
            "full_name",
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "specialization",
            "years_of_experience",
            "bio",
            "image",
            "status",
            "created_at",
            "updated_at",
        ]


class AdvisoryMemberWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating advisory member data."""
    
    class Meta:
        model = AdvisoryMember
        fields = [
            "full_name",
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "specialization",
            "years_of_experience",
            "bio",
            "image",
            "status",
        ]

    def validate_email(self, value):
        """Ensure email is unique (except for the current instance on update)."""
        instance = self.instance
        if AdvisoryMember.objects.filter(email=value).exclude(
            id=instance.id if instance else None
        ).exists():
            raise serializers.ValidationError("A member with this email already exists.")
        return value



####################### RESPONSE SERIALIZERS ########################

class StandardResponseSerializer(serializers.Serializer):
    """Standard response with detail, data, and success fields."""
    detail = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    success = serializers.BooleanField()

    class Meta:
        ref_name = "AdvisoryStandardResponseSerializer"


class AdvisoryMemberDetailResponseSerializer(serializers.Serializer):
    """Response for single advisory member detail."""
    detail = serializers.CharField()
    data = AdvisoryMemberReadSerializer()
    success = serializers.BooleanField()


class PaginatedAdvisoryMemberDataSerializer(serializers.Serializer):
    """Paginated data structure for advisory members list."""
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AdvisoryMemberReadSerializer(many=True)


class PaginatedAdvisoryMemberResponseSerializer(serializers.Serializer):
    """Legacy paginated response - kept for backward compatibility."""
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AdvisoryMemberReadSerializer(many=True)


class AdvisoryMemberListResponseSerializer(serializers.Serializer):
    """Response for advisory member list endpoint (paginated)."""
    detail = serializers.CharField()
    data = PaginatedAdvisoryMemberDataSerializer()
    success = serializers.BooleanField()


class AdvisoryMemberCreateUpdateResponseSerializer(serializers.Serializer):
    """Response for create/update advisory member operations."""
    detail = serializers.CharField()
    data = AdvisoryMemberReadSerializer()
    success = serializers.BooleanField()


class DoctorToAdvisoryRequestSerializer(serializers.Serializer):
    """Request body for creating advisory member from doctor."""
    doctor_id = serializers.UUIDField(help_text="ID of the doctor to add to advisory panel")