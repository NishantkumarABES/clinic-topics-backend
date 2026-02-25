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



class ProductCategory:
    DIAGONISTICS = 'diagnostics'
    PPE = 'ppe'
    MONITORING = 'monitoring'
    SUPPLIES = 'supplies'

    CHOICES = [
        (DIAGONISTICS, 'Diagnostics'),
        (PPE, 'PPE'),
        (MONITORING, 'Monitoring'),
        (SUPPLIES, 'Supplies'),
    ]

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
