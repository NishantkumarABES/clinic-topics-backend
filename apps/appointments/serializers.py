from rest_framework import serializers
from apps.profiles.models import DoctorProfile

class DoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name")
    gender = serializers.CharField(source="user.gender")

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "full_name",
            "gender",
            "specializations",
            "years_of_experience",
            "languages_spoken",
            "clinic_name",
            "clinic_address",
            "consultation_fee",
            "premium_online_fee",
            "verification_status",
        ]

class DoctorDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name")
    profile_photo = serializers.ImageField(source="user.profile_photo")

    class Meta:
        model = DoctorProfile
        fields = "__all__"
        read_only_fields = [
            "full_name",
            "profile_photo",
        ]

