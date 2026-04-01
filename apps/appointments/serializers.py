from rest_framework import serializers
from apps.profiles.models import DoctorProfile
from django.db.models import Avg, Count

from apps.profiles.serializers import DoctorRatingSerializer
from apps.appointments.models import AppointmentCategory

#########################   Request Serializers    #########################

class DoctorListSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    profile_photo = serializers.FileField(read_only=True)
    specialization = serializers.CharField()
    years_of_experience = serializers.IntegerField()
    clinic_name = serializers.CharField()
    clinic_address = serializers.CharField()
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    website_url = serializers.URLField()

    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "doctor_id",
            "full_name",
            "profile_photo",
            "specialization",
            "years_of_experience",
            "clinic_name",
            "clinic_address",
            "consultation_fee",
            "website_url",
            "average_rating",
            "total_ratings",
        ]

    def get_average_rating(self, obj):
        data = obj.user.ratings_received.aggregate(avg=Avg("rating"))
        return round(data["avg"] or 0, 1)

    def get_total_ratings(self, obj):
        return obj.user.ratings_received.aggregate(cnt=Count("id"))["cnt"]

class DoctorDetailSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    
    profile_photo = serializers.FileField(read_only=True)
    specialization = serializers.CharField()
    years_of_experience = serializers.IntegerField()
    credentials = serializers.CharField()
    bio = serializers.CharField()
    awards = serializers.CharField()

    clinic_name = serializers.CharField()
    clinic_address = serializers.CharField()
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    premium_online_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    consultation_duration_minutes = serializers.IntegerField()

    website_url = serializers.URLField()
    available_days = serializers.JSONField()
    available_time_slots = serializers.JSONField()

    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    ratings = serializers.SerializerMethodField()
    is_reviewed_by_user = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = [
            "doctor_id",
            "full_name",
            "email",
            "phone",
            "profile_photo",
            "specialization",
            "years_of_experience",
            "credentials",
            "bio",
            "awards",
            "clinic_name",
            "clinic_address",
            "consultation_fee",
            "premium_online_fee",
            "consultation_duration_minutes",
            "available_days",
            "available_time_slots",
            "website_url",
            "average_rating",
            "total_ratings",
            "ratings",
            "is_reviewed_by_user",
        ]

    def get_average_rating(self, obj):
        data = obj.user.ratings_received.aggregate(avg=Avg("rating"))
        return round(data["avg"] or 0, 1)

    def get_total_ratings(self, obj):
        return obj.user.ratings_received.aggregate(cnt=Count("id"))["cnt"]

    def get_ratings(self, obj):
        ratings_qs = obj.user.ratings_received.all().order_by("-created_at")
        return DoctorRatingSerializer(ratings_qs, many=True).data

    def get_is_reviewed_by_user(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user.ratings_received.filter(patient=request.user).exists()
        return False

class AppointmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentCategory
        fields = ["id", "key", "label", "image", "is_active"]

#########################   Response Serializers    #########################

class StandardResponseSerializer(serializers.Serializer):
    """Standard response format for all endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False, help_text="Response data")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "AppointmentsStandardResponseSerializer"

class PaginationMetaSerializer(serializers.Serializer):
    """Pagination metadata for list responses."""
    count = serializers.IntegerField(help_text="Total number of items")
    next = serializers.CharField(allow_null=True, help_text="URL for next page")
    previous = serializers.CharField(allow_null=True, help_text="URL for previous page")

class DoctorListDataSerializer(serializers.Serializer):
    """Data structure for paginated doctor list."""
    doctors = DoctorListSerializer(many=True)

class DoctorListResponseSerializer(serializers.Serializer):
    """Response for doctor list endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = DoctorListDataSerializer()
    success = serializers.BooleanField(help_text="Success status")
    count = serializers.IntegerField(help_text="Total number of items")
    next = serializers.CharField(allow_null=True, help_text="URL for next page")
    previous = serializers.CharField(allow_null=True, help_text="URL for previous page")

    class Meta:
        ref_name = "AppointmentsDoctorListResponseSerializer"

class DoctorDetailDataSerializer(serializers.Serializer):
    """Data structure for doctor detail response."""
    doctor = DoctorDetailSerializer()

class DoctorDetailResponseSerializer(serializers.Serializer):
    """Response for doctor detail endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = DoctorDetailDataSerializer()
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "AppointmentsDoctorDetailResponseSerializer"
