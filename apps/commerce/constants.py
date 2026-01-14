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


class PaymentMethod:
    CARD = 'card'
    UPI = 'upi'
    NETBANKING = 'netbanking'
    WALLET = 'wallet'
    COD = 'cod'

    CHOICES = [
        (CARD, 'Credit/Debit Card'),
        (UPI, 'UPI'),
        (NETBANKING, 'Net Banking'),
        (WALLET, 'Wallet'),
        (COD, 'Cash on Delivery'),
    ]


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
