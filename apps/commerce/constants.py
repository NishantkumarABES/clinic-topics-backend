from django.db import models

class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
    PAID = 'paid', 'Paid'
    PROCESSING = 'processing', 'Processing'
    SHIPPED = 'shipped', 'Shipped'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'

class PaymentGateway(models.TextChoices):
    RAZORPAY = "razorpay", "Razorpay"
    COD = "cod", "Cash on Delivery"

class PaymentMethod(models.TextChoices):
    CARD = "card", "Credit/Debit Card"
    UPI = "upi", "UPI"
    NETBANKING = "netbanking", "Net Banking"
    WALLET = "wallet", "Wallet"
    COD = "cod", "Cash on Delivery"

class RefundStatus(models.TextChoices):
    REFUND_REQUESTED = "refund_requested", "Refund Requested"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REFUND_INITIATED = "refund_initiated", "Refund Initiated"
    REFUND_COMPLETED = "refund_completed", "Refund Completed"
    FAILED = "failed", "Failed"

class ProductCategory(models.TextChoices):
    DIAGNOSTICS = 'diagnostics', 'Diagnostics'
    PPE = 'ppe', 'PPE'
    MONITORING = 'monitoring', 'Monitoring'
    SUPPLIES = 'supplies', 'Supplies'
    MEDICINE = 'medicine', 'Medicine'
    SKIN_CARE = "skin_care", 'Skin Care'
    VITAMINS_MINERALS = "vitamins_minerals", 'Vitamins & Minerals'
    BABY_CARE = "baby_care", 'Baby Care'
    PAIN_RELIEF = "pain_relief", 'Pain Relief'
    DIABETIC_CARE = "diabetic_care", 'Diabetic Care'
    PROTEIN_SUPPLEMENTS = "protein_supplements", 'Protein Supplements'
    PERSONAL_CARE_HYGIENE = "personal_care_hygiene", 'Personal Care & Hygiene'
    FITNESS_WELLNESS_EQUIPMENT = "fitness_wellness_equipment", 'Fitness & Wellness Equipment'
    
class PaymentStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    AUTHORIZED = 'authorized', 'Authorized'
    CAPTURED = 'captured', 'Captured'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'

class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed"