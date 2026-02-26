from django.db import models

class OrderStatus:
    PENDING_PAYMENT = 'pending_payment'
    PAID = 'paid'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'

    CHOICES = [
        (PENDING_PAYMENT, 'Pending Payment'),
        (PAID, 'Paid'),
        (PROCESSING, 'Processing'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
        (REFUNDED, 'Refunded'),
    ]


class PaymentGateway(models.TextChoices):
    RAZORPAY = "razorpay", "Razorpay"
    COD = "cod", "Cash on Delivery"

class PaymentMethod(models.TextChoices):
    CARD = "card", "Credit/Debit Card"
    UPI = "upi", "UPI"
    NETBANKING = "netbanking", "Net Banking"
    WALLET = "wallet", "Wallet"
    COD = "cod", "Cash on Delivery"



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
    

class PaymentStatus:
    CREATED = 'created'
    AUTHORIZED = 'authorized'
    CAPTURED = 'captured'
    FAILED = 'failed'
    REFUNDED = 'refunded'

    CHOICES = [
        (CREATED, 'Created'),
        (AUTHORIZED, 'Authorized'),
        (CAPTURED, 'Captured'),
        (FAILED, 'Failed'),
        (REFUNDED, 'Refunded'),
    ]
