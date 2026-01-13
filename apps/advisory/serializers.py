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
