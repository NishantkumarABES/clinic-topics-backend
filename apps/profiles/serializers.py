from rest_framework import serializers
from apps.profiles.models import DoctorProfile, PatientProfile
from apps.accounts.services import activate_user_if_eligible


class DoctorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    country_code = serializers.CharField(source="user.country_code", read_only=True)
    # Writable mapped fields
    date_of_birth = serializers.DateField(source="user.date_of_birth", required=False)
    gender = serializers.CharField(source="user.gender", required=False)
    
    class Meta:
        model = DoctorProfile
        exclude = ("id", "created_at", "updated_at", "user")
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        activate_user_if_eligible(user)
        return instance

class PatientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    country_code = serializers.CharField(source="user.country_code", read_only=True)
    # Writable mapped fields
    date_of_birth = serializers.DateField(source="user.date_of_birth", required=False)
    gender = serializers.CharField(source="user.gender", required=False)

    class Meta:
        model = PatientProfile
        exclude = ("id", "created_at", "updated_at", "user")

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()
        activate_user_if_eligible(user)
        return instance

class DoctorRatingCreateSerializer(serializers.Serializer):
    """Serializer for creating a doctor rating."""
    second_opinion_doctor_request_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(required=False, allow_blank=True)

    def validate_second_opinion_doctor_request_id(self, value):
        from apps.second_opinion.models import SecondOpinionDoctorRequest
        from apps.second_opinion.constants import SecondOpinionStatus

        user = self.context["request"].user

        try:
            doctor_request = SecondOpinionDoctorRequest.objects.select_related(
                "second_opinion_request", "doctor"
            ).get(id=value)
        except SecondOpinionDoctorRequest.DoesNotExist:
            raise serializers.ValidationError("Doctor request not found")

        # Verify patient owns this request
        if doctor_request.second_opinion_request.patient != user:
            raise serializers.ValidationError("You can only rate your own requests")

        # Verify request is completed
        if doctor_request.status != SecondOpinionStatus.COMPLETED:
            raise serializers.ValidationError(
                "Can only rate after doctor has responded"
            )

        # Check if already rated
        if hasattr(doctor_request, "rating"):
            raise serializers.ValidationError("Already rated this request")

        self._doctor_request = doctor_request
        return value

    def validate(self, data):
        data["_doctor_request"] = self._doctor_request
        return data

    def create(self, validated_data):
        from apps.profiles.models import DoctorRating

        doctor_request = validated_data.pop("_doctor_request")

        rating = DoctorRating.objects.create(
            doctor=doctor_request.doctor,
            patient=self.context["request"].user,
            second_opinion_doctor_request=doctor_request,
            rating=validated_data["rating"],
            review=validated_data.get("review", "")
        )
        return rating

class DoctorRatingSerializer(serializers.ModelSerializer):
    """Serializer for displaying doctor ratings."""
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        from apps.profiles.models import DoctorRating
        model = DoctorRating
        fields = [
            "id", "patient_name", "rating", "review", "created_at"
        ]
        read_only_fields = fields

class DoctorAverageRatingSerializer(serializers.Serializer):
    """Serializer for doctor's aggregate rating info."""
    average_rating = serializers.FloatField()
    total_ratings = serializers.IntegerField()
    rating_breakdown = serializers.DictField()

class SimpleDoctorReviewCreateSerializer(serializers.Serializer):
    """
    Simple leave review serializer (no second opinion linking).
    """
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        from apps.accounts.models import User
        from apps.accounts.constants import UserRole
        from apps.profiles.models import DoctorRating

        request = self.context["request"]
        doctor_id = self.context["doctor_id"]

        # Validate doctor exists
        try:
            doctor = User.objects.get(id=doctor_id, role=UserRole.DOCTOR)
        except User.DoesNotExist:
            raise serializers.ValidationError("Doctor not found")

        # Prevent duplicate review (recommended)
        if DoctorRating.objects.filter(
            doctor=doctor,
            patient=request.user,
            second_opinion_doctor_request__isnull=True
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this doctor"
            )

        data["doctor"] = doctor
        return data

    def create(self, validated_data):
        from apps.profiles.models import DoctorRating

        return DoctorRating.objects.create(
            doctor=validated_data["doctor"],
            patient=self.context["request"].user,
            rating=validated_data["rating"],
            review=validated_data.get("review", ""),
        )

#########################   Response Serializers    #########################

class StandardResponseSerializer(serializers.Serializer):
    """Standard API response format."""
    detail = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    success = serializers.BooleanField()

    class Meta:
        ref_name = "ProfilesStandardResponseSerializer"

class DoctorProfileResponseSerializer(serializers.Serializer):
    """Response for doctor profile endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = DoctorProfileSerializer()
    success = serializers.BooleanField(help_text="Success status")

class PatientProfileResponseSerializer(serializers.Serializer):
    """Response for patient profile endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = PatientProfileSerializer()
    success = serializers.BooleanField(help_text="Success status")

class RatingDataSerializer(serializers.Serializer):
    """Data returned in rating creation response."""
    rating_id = serializers.CharField(help_text="ID of the created rating")

class RatingCreateResponseSerializer(serializers.Serializer):
    """Response for rating creation endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = RatingDataSerializer(allow_null=True, required=False)
    success = serializers.BooleanField(help_text="Success status")

class RatingsListDataSerializer(serializers.Serializer):
    """Data returned in ratings list response."""
    doctor_id = serializers.CharField(help_text="Doctor ID")
    doctor_name = serializers.CharField(help_text="Doctor's full name")
    ratings = DoctorRatingSerializer(many=True)
    average_rating = serializers.FloatField(help_text="Average rating")
    total_ratings = serializers.IntegerField(help_text="Total number of ratings")
    rating_breakdown = serializers.DictField(help_text="Rating breakdown by stars")

class RatingsListResponseSerializer(serializers.Serializer):
    """Response for ratings list endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = RatingsListDataSerializer()
    success = serializers.BooleanField(help_text="Success status")
