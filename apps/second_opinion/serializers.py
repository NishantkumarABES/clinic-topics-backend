from rest_framework import serializers
from django.db import transaction
from django.db import models
from decimal import Decimal

from apps.second_opinion.models import SecondOpinionRequest, SecondOpinionDoctorRequest, SecondOpinionDocument, SecondOpinionPayment
from apps.second_opinion.constants import SecondOpinionStatus, SecondOpinionPaymentStatus, DocumentType
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from apps.profiles.models import DoctorRating


# ===================== Input Serializers =====================

class CalculateChargesSerializer(serializers.Serializer):
    """Serializer for calculating total consultation charges."""
    doctor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of doctor UUIDs to get second opinion from"
    )

    def validate_doctor_ids(self, value):
        # Verify all doctors exist and are actually doctors
        doctors = User.objects.filter(
            id__in=value,
            role=UserRole.DOCTOR
        ).select_related("doctor_profile")

        if len(doctors) != len(value):
            raise serializers.ValidationError(
                "One or more doctor IDs are invalid"
            )

        # Check all doctors have profiles with fees
        for doctor in doctors:
            if not hasattr(doctor, "doctor_profile"):
                raise serializers.ValidationError(
                    f"Doctor {doctor.full_name} does not have a complete profile"
                )

        return value

class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for individual document upload."""
    file = serializers.FileField()
    file_type = serializers.ChoiceField(
        choices=DocumentType.CHOICES,
        default=DocumentType.OTHER
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )

class CreateSecondOpinionRequestSerializer(serializers.Serializer):
    """Serializer for creating a new second opinion request."""
    doctor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of doctor UUIDs"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )
    question = serializers.CharField(
        min_length=10,
        help_text="Your specific question for doctors"
    )

    def validate_doctor_ids(self, value):
        # Verify all doctors exist
        doctors = User.objects.filter(
            id__in=value,
            role=UserRole.DOCTOR
        ).select_related("doctor_profile")

        if len(doctors) != len(value):
            raise serializers.ValidationError(
                "One or more doctor IDs are invalid"
            )

        # Store doctors for use in create
        self._doctors = doctors
        return value

    def validate(self, data):
        data["_doctors"] = getattr(self, "_doctors", [])
        return data

    @transaction.atomic
    def create(self, validated_data):
        patient = self.context["request"].user
        doctors = validated_data.pop("_doctors")

        # Calculate total amount
        total_amount = Decimal("0.00")
        doctor_fees = {}

        for doctor in doctors:
            fee = doctor.doctor_profile.premium_online_fee or Decimal("0.00")
            total_amount += fee
            doctor_fees[doctor.id] = fee

        # Create main request
        second_opinion_request = SecondOpinionRequest.objects.create(
            patient=patient,
            notes=validated_data.get("notes", ""),
            question=validated_data["question"],
            total_amount=total_amount,
            payment_status=SecondOpinionPaymentStatus.PENDING
        )

        # Create individual doctor requests
        doctor_requests = []
        for doctor in doctors:
            doctor_request = SecondOpinionDoctorRequest(
                second_opinion_request=second_opinion_request,
                doctor=doctor,
                consultation_fee=doctor_fees[doctor.id],
                status=SecondOpinionStatus.SUBMITTED
            )
            doctor_requests.append(doctor_request)

        SecondOpinionDoctorRequest.objects.bulk_create(doctor_requests)

        return second_opinion_request


# ===================== Output Serializers =====================

class DoctorBasicInfoSerializer(serializers.ModelSerializer):
    """Basic doctor information for display."""
    specialization = serializers.SerializerMethodField()
    consultation_fee = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "full_name", "email",
            "specialization", "consultation_fee",
            "profile_photo", "average_rating",
            "total_ratings",
        ]

    def get_specialization(self, obj):
        if hasattr(obj, "doctor_profile"):
            return obj.doctor_profile.specialization
        return None

    def get_consultation_fee(self, obj):
        if hasattr(obj, "doctor_profile"):
            return obj.doctor_profile.premium_online_fee
        return None

    def get_profile_photo(self, obj):
        if hasattr(obj, "doctor_profile") and obj.doctor_profile.profile_photo:
            return obj.doctor_profile.profile_photo.url
        return None

    def get_average_rating(self, obj):
        return round(obj.avg_rating, 2) if obj.avg_rating else 0.0

    def get_total_ratings(self, obj):
        return obj.total_ratings or 0

class SecondOpinionDocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents."""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SecondOpinionDocument
        fields = [
            "id", "file_name", "file_type",
            "description", "file_url", "created_at"
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

class SecondOpinionDoctorRequestSerializer(serializers.ModelSerializer):
    """Serializer for individual doctor request."""
    doctor = DoctorBasicInfoSerializer(read_only=True)

    class Meta:
        model = SecondOpinionDoctorRequest
        fields = [
            "id", "doctor", "status", "consultation_fee",
            "response", "responded_at", "created_at"
        ]

class SecondOpinionRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing second opinion requests."""
    doctors_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = SecondOpinionRequest
        fields = [
            "id", "question", "total_amount", "payment_status",
            "is_paid", "doctors_count", "completed_count",
            "created_at", "updated_at"
        ]

class SecondOpinionRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all doctor requests and documents."""
    doctor_requests = SecondOpinionDoctorRequestSerializer(
        many=True,
        read_only=True
    )
    documents = SecondOpinionDocumentSerializer(
        many=True,
        read_only=True
    )
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = SecondOpinionRequest
        fields = [
            "id", "notes", "question", "total_amount",
            "payment_status", "is_paid", "doctor_requests",
            "documents", "created_at", "updated_at"
        ]

class CalculateChargesResponseSerializer(serializers.Serializer):
    """Response for charge calculation."""
    doctors = serializers.ListField(child=serializers.DictField())
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default="INR")

class SecondOpinionPaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""
    class Meta:
        model = SecondOpinionPayment
        fields = [
            "id", "razorpay_order_id", "razorpay_payment_id",
            "amount", "currency", "status", "created_at"
        ]
        read_only_fields = fields


# ===================== Payment Serializers =====================

class CreatePaymentOrderSerializer(serializers.Serializer):
    """Serializer for creating a payment order."""
    second_opinion_request_id = serializers.UUIDField()

    def validate_second_opinion_request_id(self, value):
        user = self.context["request"].user

        try:
            request = SecondOpinionRequest.objects.get(
                id=value,
                patient=user
            )
        except SecondOpinionRequest.DoesNotExist:
            raise serializers.ValidationError(
                "Second opinion request not found"
            )

        if request.payment_status == SecondOpinionPaymentStatus.COMPLETED:
            raise serializers.ValidationError(
                "Payment already completed for this request"
            )

        self._second_opinion_request = request
        return value

    def validate(self, data):
        data["_second_opinion_request"] = self._second_opinion_request
        return data
    
    class Meta:
        ref_name = "SecondOpinionCreatePaymentOrderSerializer"

class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for verifying payment."""
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

    def validate_razorpay_order_id(self, value):
        request = self.context["request"]

        try:
            payment = SecondOpinionPayment.objects.select_related(
                "second_opinion_request"
            ).get(razorpay_order_id=value)
        except SecondOpinionPayment.DoesNotExist:
            raise serializers.ValidationError("Payment order not found")

        # ✅ Ownership check
        if payment.second_opinion_request.patient != request.user:
            raise serializers.ValidationError("Unauthorized payment verification attempt")

        if payment.status == SecondOpinionPaymentStatus.COMPLETED:
            raise serializers.ValidationError("Payment already verified")

        self._payment = payment
        return value

    def validate(self, data):
        data["_payment"] = self._payment
        return data

    class Meta:
        ref_name = "SecondOpinionVerifyPaymentSerializer"


# ===================== Doctor Side Serializers =====================

class PatientBasicInfoSerializer(serializers.ModelSerializer):
    """Basic patient info for doctor-side display."""

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]

class DoctorSecondOpinionListSerializer(serializers.ModelSerializer):
    """List serializer for doctors to see incoming requests."""

    patient = PatientBasicInfoSerializer(
        source="second_opinion_request.patient",
        read_only=True
    )
    question = serializers.CharField(
        source="second_opinion_request.question",
        read_only=True
    )
    created_at = serializers.DateTimeField(
        source="second_opinion_request.created_at",
        read_only=True
    )

    class Meta:
        model = SecondOpinionDoctorRequest
        fields = [
            "id",
            "patient",
            "question",
            "status",
            "consultation_fee",
            "created_at"
        ]

class DoctorSecondOpinionDetailSerializer(serializers.ModelSerializer):
    """Detailed view for a doctor to review a case."""

    patient = PatientBasicInfoSerializer(
        source="second_opinion_request.patient",
        read_only=True
    )
    notes = serializers.CharField(
        source="second_opinion_request.notes",
        read_only=True
    )
    question = serializers.CharField(
        source="second_opinion_request.question",
        read_only=True
    )
    documents = SecondOpinionDocumentSerializer(
        source="second_opinion_request.documents",
        many=True,
        read_only=True
    )

    class Meta:
        model = SecondOpinionDoctorRequest
        fields = [
            "id",
            "patient",
            "notes",
            "question",
            "documents",
            "status",
            "consultation_fee",
            "response",
            "responded_at",
            "created_at"
        ]

class DoctorStartReviewSerializer(serializers.Serializer):
    """Serializer to mark request as in-review."""

    def save(self, **kwargs):
        doctor_request = self.context["doctor_request"]
        doctor_request.mark_in_review()
        return doctor_request

class DoctorSubmitResponseSerializer(serializers.Serializer):
    """Serializer for doctor submitting opinion."""

    response = serializers.CharField(min_length=20)

    def save(self, **kwargs):
        doctor_request = self.context["doctor_request"]
        response_text = self.validated_data["response"]
        doctor_request.mark_completed(response_text)
        return doctor_request

# ====================== Doctor rating Serializer =======================
class DoctorRatingSerializer(serializers.ModelSerializer):
    second_opinion_doctor_request_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = DoctorRating
        fields = [
            "id",
            "second_opinion_doctor_request_id",
            "rating",
            "review",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]
        ref_name = "DoctorRatingSerializer"

    def validate_second_opinion_doctor_request_id(self, value):
        request = self.context["request"]

        try:
            doctor_request = SecondOpinionDoctorRequest.objects.select_related(
                "second_opinion_request", "doctor"
            ).get(id=value)
        except SecondOpinionDoctorRequest.DoesNotExist:
            raise serializers.ValidationError("Second opinion request not found")

        # Ensure the logged-in user owns the request
        if doctor_request.second_opinion_request.patient != request.user:
            raise serializers.ValidationError("You are not allowed to rate this request")

        # Ensure request is completed
        if doctor_request.status != SecondOpinionStatus.COMPLETED:
            raise serializers.ValidationError("Doctor has not completed this request yet")

        # Prevent duplicate rating (OneToOneField enforces this too, but we validate early)
        if hasattr(doctor_request, "rating"):
            raise serializers.ValidationError("Rating already submitted for this request")

        self._doctor_request = doctor_request
        return value

    def create(self, validated_data):
        request = self.context["request"]
        doctor_request = self._doctor_request

        rating = DoctorRating.objects.create(
            doctor=doctor_request.doctor,
            patient=request.user,
            second_opinion_doctor_request=doctor_request,
            rating=validated_data["rating"],
            review=validated_data.get("review", "")
        )

        return rating

    
        