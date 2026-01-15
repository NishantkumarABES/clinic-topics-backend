from rest_framework import serializers
from apps.profiles.models import DoctorProfile
from django.db.models import Avg, Count


class DoctorListSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

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

    class Meta:
        model = DoctorProfile
        fields = [
            "doctor_id",
            "full_name",
            "email",
            "phone",
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
        ]

    def get_average_rating(self, obj):
        data = obj.user.ratings_received.aggregate(avg=Avg("rating"))
        return round(data["avg"] or 0, 1)

    def get_total_ratings(self, obj):
        return obj.user.ratings_received.aggregate(cnt=Count("id"))["cnt"]
