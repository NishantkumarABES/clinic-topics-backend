from rest_framework import serializers
from apps.advertisements.models import Advertisement


class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = ['id', 'title', 'url', 'image', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_url(self, value):
        """Ensure URL is valid"""
        if not value:
            raise serializers.ValidationError("URL is required")
        return value


class AdvertisementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing advertisements"""
    class Meta:
        model = Advertisement
        fields = ['id', 'title', 'url', 'image', 'status', 'created_at', 'updated_at']
