from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from core.models import TimeStampedUUIDModel
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.second_opinion.constants import (
    SecondOpinionStatus, SecondOpinionPaymentStatus, DocumentType, DiscountType
)


class PaidDoctorRequestQuerySet(models.QuerySet):
    def paid(self):
        return self.filter(
            second_opinion_request__payment_status=SecondOpinionPaymentStatus.COMPLETED
        )

class SecondOpinionRequest(TimeStampedUUIDModel):
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="second_opinion_requests",
        limit_choices_to={"role": UserRole.PATIENT}
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional context or medical history"
    )
    question = models.TextField(
        help_text="Specific question for doctors"
    )

    # Payment information
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total consultation charges for all selected doctors"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=SecondOpinionPaymentStatus.CHOICES,
        default=SecondOpinionPaymentStatus.PENDING
    )

    status = models.CharField(
        max_length=20,
        choices=SecondOpinionStatus.CHOICES,
        default=SecondOpinionStatus.SUBMITTED
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Second Opinion Request"
        verbose_name_plural = "Second Opinion Requests"

    def __str__(self):
        return f"SecondOpinion({self.patient.full_name}) - {self.created_at.date()}"

    @property
    def is_paid(self):
        return self.payment_status == SecondOpinionPaymentStatus.COMPLETED

    @property
    def doctors_count(self):
        return self.doctor_requests.count()

    @property
    def completed_count(self):
        return self.doctor_requests.filter(
            status=SecondOpinionStatus.COMPLETED
        ).count()
    
    @property
    def documents_count(self):
        return self.documents.count()

class SecondOpinionDoctorRequest(TimeStampedUUIDModel):
    second_opinion_request = models.ForeignKey(
        SecondOpinionRequest,
        on_delete=models.CASCADE,
        related_name="doctor_requests"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_second_opinions",
        limit_choices_to={"role": UserRole.DOCTOR}
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=SecondOpinionStatus.CHOICES,
        default=SecondOpinionStatus.SUBMITTED
    )

    # Fee for this doctor's consultation
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    # Doctor's response
    response = models.JSONField(
        blank=True,
        null=True,
        help_text="Doctor structured response: findings, observations, medical_opinion, answer_to_patient"
    )
    
    responded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("second_opinion_request", "doctor")
        verbose_name = "Doctor Request"
        verbose_name_plural = "Doctor Requests"

    objects = PaidDoctorRequestQuerySet.as_manager()

    def __str__(self):
        return f"Request to Dr. {self.doctor.full_name} - {self.status}"
    
    def mark_in_review(self):
        """Doctor starts reviewing the case."""
        if self.status == SecondOpinionStatus.IN_REVIEW:
            return
        if self.status != SecondOpinionStatus.SUBMITTED:
            raise ValueError("Only submitted requests can be moved to in-review")
        self.status = SecondOpinionStatus.IN_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def mark_completed(self, response_text: str):
        """Doctor submits final opinion."""
        if self.status not in [SecondOpinionStatus.SUBMITTED, SecondOpinionStatus.IN_REVIEW]:
            raise ValueError("Only active requests can be completed")
        self.status = SecondOpinionStatus.COMPLETED
        self.response = response_text
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "response", "responded_at", "updated_at"])
    
    @property
    def is_completed(self):
        return self.status == SecondOpinionStatus.COMPLETED

class SecondOpinionDocument(TimeStampedUUIDModel):
    second_opinion_request = models.ForeignKey(
        SecondOpinionRequest,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    file = models.FileField(
        upload_to="second_opinion_documents/"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    file_type = models.CharField(
        max_length=20,
        choices=DocumentType.CHOICES,
        default=DocumentType.OTHER
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Brief description of the document"
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.file_name} ({self.file_type})"

class SecondOpinionPayment(TimeStampedUUIDModel):
    second_opinion_request = models.OneToOneField(
        SecondOpinionRequest,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    # Razorpay integration
    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True
    )
    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    currency = models.CharField(
        max_length=10,
        default="INR"
    )
    status = models.CharField(
        max_length=20,
        choices=SecondOpinionPaymentStatus.CHOICES,
        default=SecondOpinionPaymentStatus.PENDING
    )
    failure_reason = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status}"

class Coupon(TimeStampedUUIDModel):
    code = models.CharField(
        max_length=50,
        unique=True
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    usage_limit = models.IntegerField(
        null=True,
        blank=True
    )

    used_count = models.IntegerField(
        default=0
    )

    valid_from = models.DateTimeField()

    valid_until = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def is_valid(self, order_amount):

        if not self.is_active:
            return False

        now = timezone.now()

        if now < self.valid_from or now > self.valid_until:
            return False

        if order_amount < self.minimum_order_amount:
            return False

        if self.usage_limit and self.used_count >= self.usage_limit:
            return False

        return True

    def calculate_discount(self, amount):

        if self.discount_type == self.DISCOUNT_TYPE_PERCENTAGE:

            discount = (amount * self.discount_value) / Decimal("100")

            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)

        else:
            discount = self.discount_value

        return min(discount, amount)

class CouponUsage(TimeStampedUUIDModel):

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="usages"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    second_opinion_request = models.OneToOneField(
        "second_opinion.SecondOpinionRequest",
        on_delete=models.CASCADE,
        related_name="coupon_usage"
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )