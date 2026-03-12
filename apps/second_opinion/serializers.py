from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from apps.second_opinion.models import SecondOpinionRequest, SecondOpinionDoctorRequest, SecondOpinionDocument, SecondOpinionPayment, Coupon
from apps.second_opinion.constants import SecondOpinionStatus, SecondOpinionPaymentStatus, DocumentType
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from apps.profiles.models import DoctorRating
from apps.notifications.services import create_user_notification


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
    doctor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    question = serializers.CharField(min_length=10)

    # Swagger-safe single FileField, multiple handled manually
    documents = serializers.FileField(write_only=True, required=True)

    document_types = serializers.ListField(
        child=serializers.ChoiceField(choices=DocumentType.CHOICES),
        required=False
    )
    document_descriptions = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False
    )

    # ---------- Doctor validation ----------
    def validate_doctor_ids(self, value):
        doctors = User.objects.filter(
            id__in=value,
            role=UserRole.DOCTOR
        ).select_related("doctor_profile")

        if len(doctors) != len(value):
            raise serializers.ValidationError("One or more doctor IDs are invalid")

        for doctor in doctors:
            if not hasattr(doctor, "doctor_profile"):
                raise serializers.ValidationError(
                    f"Doctor {doctor.full_name} does not have a complete profile"
                )

        # Store queryset for create()
        self._doctors = doctors
        return value

    # ---------- General validation ----------
    def validate(self, data):
        files = self.context["request"].FILES.getlist("documents")
        if not files:
            raise serializers.ValidationError("At least one document is required")

        data["_documents"] = files
        data["_doctors"] = self._doctors
        return data

    # ---------- Create implementation ----------
    @transaction.atomic
    def create(self, validated_data):
        patient = self.context["request"].user
        doctors = validated_data.pop("_doctors")
        documents = validated_data.pop("_documents")

        document_types = validated_data.pop("document_types", [])
        document_descriptions = validated_data.pop("document_descriptions", [])

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
            status=SecondOpinionStatus.SUBMITTED
        )

        # Create doctor requests
        doctor_requests = SecondOpinionDoctorRequest.objects.bulk_create([
            SecondOpinionDoctorRequest(
                second_opinion_request=second_opinion_request,
                doctor=doctor,
                consultation_fee=doctor_fees[doctor.id]
            )
            for doctor in doctors
        ])
        for dr in doctor_requests:
            create_user_notification(
                recipient=dr.doctor,
                title="New Second Opinion Request",
                message=f"You have received a new second opinion request from {patient.full_name}.",
                data={
                    "type": "SECOND_OPINION_REQUEST",
                    "request_id": str(second_opinion_request.id),
                    "doctor_request_id": str(dr.id)
                }
            )

        # Save uploaded documents
        for i, doc in enumerate(documents):
            SecondOpinionDocument.objects.create(
                second_opinion_request=second_opinion_request,
                file=doc,
                file_name=doc.name,
                file_type=document_types[i] if i < len(document_types) else DocumentType.OTHER,
                description=document_descriptions[i] if i < len(document_descriptions) else ""
            )

        return second_opinion_request


# ===================== Output Serializers =====================

class DoctorBasicInfoSerializer(serializers.ModelSerializer):
    """Basic doctor information for display."""
    specialization = serializers.SerializerMethodField()
    consultation_fee = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    years_of_experience = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "full_name", "email",
            "specialization", "consultation_fee",
            "profile_photo", "average_rating",
            "total_ratings", "years_of_experience",
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
    
    def get_years_of_experience(self, obj):
        if hasattr(obj, "doctor_profile"):
            return obj.doctor_profile.years_of_experience
        return None

    def get_average_rating(self, obj):
        avg = getattr(obj, "avg_rating", None)
        return round(avg, 2) if avg else 0.0

    def get_total_ratings(self, obj):
        total = getattr(obj, "total_ratings", None)
        return total or 0

class SecondOpinionDocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents."""
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = SecondOpinionDocument
        fields = [
            "id", "file_name", "file_type", "file_size",
            "description", "file_url", "created_at"
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None
    
    def get_file_size(self, obj):
        if obj.file:
            return obj.file.size  
        return 0

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
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SecondOpinionRequest
        fields = [
            "id", "question", "total_amount", "payment_status",
            "status", "is_paid", "doctors_count", "completed_count", 
            "documents_count", "created_at", "updated_at"
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
            "id", "notes", "question", "total_amount", "status",    
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
        fields = ["id", "full_name", "email", "phone", "date_of_birth", "gender"]

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
    findings = serializers.CharField()
    observations = serializers.CharField()
    medical_opinion = serializers.CharField()
    answer_to_patient = serializers.CharField()

    def validate(self, attrs):
        doctor_request = self.context["doctor_request"]

        if doctor_request.status != SecondOpinionStatus.IN_REVIEW:
            raise serializers.ValidationError(
                "Request must be in_review to submit response."
            )
        return attrs

    def save(self):
        doctor_request = self.context["doctor_request"]

        response_json = {
            "findings": self.validated_data["findings"],
            "observations": self.validated_data["observations"],
            "medical_opinion": self.validated_data["medical_opinion"],
            "answer_to_patient": self.validated_data["answer_to_patient"]
        }

        doctor_request.mark_completed(response_json)

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


# ===================== Response Serializers =====================

class StandardResponseSerializer(serializers.Serializer):
    """
    Base response serializer with {detail, data, success}.
    Used for simple message-only responses.
    """
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False)
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "SecondOpinionStandardResponseSerializer"


# ---------- Calculate Charges ----------

class CalculateChargesDataSerializer(serializers.Serializer):
    doctors = serializers.ListField(child=serializers.DictField())
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default="INR")


class CalculateChargesResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(default="Charges calculated successfully")
    data = CalculateChargesDataSerializer()
    success = serializers.BooleanField(default=True)

    class Meta:
        ref_name = "SecondOpinionCalculateChargesResponseSerializer"


# ---------- Second Opinion Request List ----------

class SecondOpinionRequestListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = SecondOpinionRequestListSerializer(many=True)

class SecondOpinionRequestListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = SecondOpinionRequestListDataSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionRequestListResponseSerializer"


# ---------- Second Opinion Request Detail ----------

class SecondOpinionRequestDetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = SecondOpinionRequestDetailSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionRequestDetailResponseSerializer"

# ---------- Payment Order ----------

class PaymentOrderDataSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField(default="INR")
    key_id = serializers.CharField()
    payment_id = serializers.UUIDField()

class PaymentOrderResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = PaymentOrderDataSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionPaymentOrderResponseSerializer"


# ---------- Payment Verification ----------

class PaymentVerificationDataSerializer(serializers.Serializer):
    second_opinion_request_id = serializers.UUIDField()

class PaymentVerificationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = PaymentVerificationDataSerializer(allow_null=True)
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionPaymentVerificationResponseSerializer"


# ---------- Doctor List ----------

class DoctorBasicInfoListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DoctorBasicInfoSerializer(many=True)

class DoctorBasicInfoListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = DoctorBasicInfoListDataSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionDoctorBasicInfoListResponseSerializer"


# ---------- Doctor Side Lists ----------

class DoctorSecondOpinionListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DoctorSecondOpinionListSerializer(many=True)

class DoctorSecondOpinionListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = DoctorSecondOpinionListDataSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionDoctorSecondOpinionListResponseSerializer"

class DoctorSecondOpinionDetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = DoctorSecondOpinionDetailSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionDoctorSecondOpinionDetailResponseSerializer"

# ---------- Doctor Rating ----------

class DoctorRatingResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = DoctorRatingSerializer()
    success = serializers.BooleanField()

    class Meta:
        ref_name = "SecondOpinionDoctorRatingResponseSerializer"


# ---------- Coupon Management ----------

class ApplyCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(max_length=50)
    doctor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )

    def validate_coupon_code(self, value):
        try:
            coupon = Coupon.objects.get(code__iexact=value.strip())
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code")

        self._coupon = coupon
        return value

    def validate_doctor_ids(self, value):
        doctors = User.objects.filter(
            id__in=value,
            role=UserRole.DOCTOR
        ).select_related("doctor_profile")

        if len(doctors) != len(value):
            raise serializers.ValidationError(
                "One or more doctor IDs are invalid"
            )

        self._doctors = doctors
        return value

    def validate(self, data):
        coupon = self._coupon
        doctors = self._doctors
        total_amount = Decimal("0.00")
        for doctor in doctors:
            fee = doctor.doctor_profile.premium_online_fee or Decimal("0.00")
            total_amount += fee

        if not coupon.is_valid(total_amount):
            raise serializers.ValidationError(
                "Coupon is not valid for this order"
            )

        discount = coupon.calculate_discount(total_amount)

        data["coupon"] = coupon
        data["total_amount"] = total_amount
        data["discount_amount"] = discount
        data["final_amount"] = total_amount - discount

        return data
    
    class Meta:
        ref_name = "SecondOpinionApplyCouponSerializer"

class AdminCouponListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "minimum_order_amount",
            "usage_limit",
            "used_count",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at"
        ]

class AdminCouponResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "minimum_order_amount",
            "usage_limit",
            "used_count",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at",
            "updated_at"
        ]

class AdminCouponCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "minimum_order_amount",
            "usage_limit",
            "valid_from",
            "valid_until",
            "is_active"
        ]
        read_only_fields = ["id"]

    def validate(self, data):

        valid_from = data.get("valid_from")
        valid_until = data.get("valid_until")

        if valid_from and valid_until and valid_until <= valid_from:
            raise serializers.ValidationError(
                "valid_until must be greater than valid_from"
            )

        if valid_until and valid_until < timezone.now():
            raise serializers.ValidationError(
                "Coupon expiry must be in the future"
            )

        return data

class AdminCouponUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Coupon
        fields = [
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "minimum_order_amount",
            "usage_limit",
            "valid_from",
            "valid_until",
            "is_active"
        ]

class AdminCouponListDataSerializer(serializers.Serializer):

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AdminCouponListSerializer(many=True)

class AdminCouponListResponseSerializer(serializers.Serializer):

    detail = serializers.CharField()
    data = AdminCouponListDataSerializer()
    success = serializers.BooleanField()