from rest_framework import serializers
from apps.profiles.models import DoctorProfile, PatientProfile


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



















# class DoctorProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         exclude = ("user", "created_at", "updated_at")

#     def validate_years_of_experience(self, value):
#         if value < 0:
#             raise serializers.ValidationError("Invalid experience")
#         return value

#     def validate_consultation_duration_minutes(self, value):
#         if value is not None and value <= 0:
#             raise serializers.ValidationError("Duration must be positive")
#         return value
    
#     def validate_consultation_fee(self, value):
#         if value is not None and value <= 0:
#             raise serializers.ValidationError("Fee must be positive")
#         return value
    
# class DoctorOverviewSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "credentials",
#             "specialization",
#             "years_of_experience",
#         ]

# class DoctorProfessionalSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "qualifications",
#             "areas_of_expertise",
#             "conditions_treated",
#             "professional_memberships",
#             "publications",
#         ]

# class DoctorLicenseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "license_number",
#             "medical_council",
#             "registration_numbers",
#             "license_issue_year",
#             "license_document",
#         ]

# class DoctorPracticeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "clinic_name",
#             "clinic_address",
#             "clinic_location",
#             "clinic_photos",
#             "consultation_fee",
#             "premium_online_fee",
#             "consultation_duration_minutes",
#         ]

# class DoctorAvailabilitySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "available_days",
#             "available_time_slots",
#         ]

# class DoctorAboutSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorProfile
#         fields = [
#             "bio",
#             "awards",
#         ]


# class PatientProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PatientProfile
#         exclude = ("user", "created_at", "updated_at")

#     def validate_emergency_contact_phone(self, value):
#         if value and not value.isdigit():
#             raise serializers.ValidationError("Invalid phone number")
#         return value

# class PatientPersonalSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PatientProfile
#         fields = [
#             "blood_group",
#             "address",
#         ]

# class PatientMedicalSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PatientProfile
#         fields = [
#             "medical_history",
#             "current_medications",
#             "allergies",
#             "chronic_conditions",
#             "previous_surgeries",
#             "family_medical_history",
#         ]

# class PatientEmergencySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PatientProfile
#         fields = [
#             "emergency_contact_name",
#             "emergency_contact_relationship",
#             "emergency_contact_phone",
#         ]

# class PatientInsuranceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PatientProfile
#         fields = [
#             "insurance_provider",
#             "insurance_policy_number",
#             "insurance_coverage_details",
#         ]
