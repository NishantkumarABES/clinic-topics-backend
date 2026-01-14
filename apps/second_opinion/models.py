from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.second_opinion.constants import (
    SecondOpinionStatus, SecondOpinionPaymentStatus, DocumentType
)


class SecondOpinionRequest(TimeStampedUUIDModel):
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="second_opinion_requests",
        limit_choices_to={"role": "patient"}
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
        limit_choices_to={"role": "doctor"}
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
    response = models.TextField(
        blank=True,
        null=True,
        help_text="Doctor's second opinion response"
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

    def __str__(self):
        return f"Request to Dr. {self.doctor.full_name} - {self.status}"

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
    second_opinion_request = models.ForeignKey(
        SecondOpinionRequest,
        on_delete=models.CASCADE,
        related_name="payments"
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
