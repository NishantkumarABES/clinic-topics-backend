from rest_framework import serializers
from apps.profiles.models import DoctorProfile, PatientProfile


class DoctorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    country_code = serializers.CharField(source="user.country_code", read_only=True)
    date_of_birth = serializers.DateField(source="user.date_of_birth", read_only=True)
    gender = serializers.CharField(source="user.gender", read_only=True)
    
    class Meta:
        model = DoctorProfile
        exclude = ("id", "created_at", "updated_at", "user")


class PatientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    country_code = serializers.CharField(source="user.country_code", read_only=True)
    date_of_birth = serializers.DateField(source="user.date_of_birth", read_only=True)
    gender = serializers.CharField(source="user.gender", read_only=True)

    class Meta:
        model = PatientProfile
        exclude = ("id", "created_at", "updated_at", "user")

    


















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
