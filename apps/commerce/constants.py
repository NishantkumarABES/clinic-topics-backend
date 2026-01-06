class OrderStatus:
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELED = 'canceled'

    CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELED, 'Canceled'),
    ]


class PaymentMethod:
    CREDIT_CARD = 'credit_card'
    PAYPAL = 'paypal'
    BANK_TRANSFER = 'bank_transfer'

    CHOICES = [
        (CREDIT_CARD, 'Credit Card'),
        (PAYPAL, 'PayPal'),
        (BANK_TRANSFER, 'Bank Transfer'),
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