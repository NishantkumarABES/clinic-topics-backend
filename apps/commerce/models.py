from django.db import models, transaction
from django.db.models import Deferrable
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

from core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.commerce.constants import (
    ProductCategory, OrderStatus, PaymentStatus, PaymentGateway, PaymentMethod, RefundStatus
)

class Product(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    # SKU stands for Stock Keeping Unit, a unique identifier for each product in inventory.

    category = models.CharField(
        max_length=50,
        choices=ProductCategory.choices
    )
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)
    # is_out_of_stock = models.BooleanField(default=False)
    stock_quantity = models.PositiveIntegerField(default=0)
    for_patients = models.BooleanField(default=True)
    for_doctors = models.BooleanField(default=True)
    is_refundable = models.BooleanField(default=True)

    max_user_quantity = models.PositiveIntegerField(
        default=5,
        help_text="Maximum quantity a single user can add to cart"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "brand"],
                name="unique_product_name_brand"
            )
        ]
        ordering = ["-created_at"]
    
    @property
    def is_out_of_stock(self):
        return self.stock_quantity <= 0
    
    def get_unit_final_price(self):
        price = self.price

        if self.discount_percentage > 0:
            price -= (price * self.discount_percentage / Decimal("100"))

        if self.tax_percentage > 0:
            price += (price * self.tax_percentage / Decimal("100"))

        return round(price, 2)

    def __str__(self):
        return self.name

class ProductImage(TimeStampedUUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/")

class ProductReview(TimeStampedUUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    rating = models.PositiveIntegerField()  # 1–5
    comment = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)

    class Meta:
        unique_together = ("product", "user")

class Coupon(TimeStampedUUIDModel):

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed"

    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Discount definition
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )

    # Usage limits
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    current_uses = models.PositiveIntegerField(default=0)

    # Cart conditions
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Validity
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    def is_valid(self, cart_total=None):
        now = timezone.now()

        if not self.is_active:
            return False

        if now < self.valid_from or now > self.valid_until:
            return False

        if self.max_uses is not None and self.current_uses >= self.max_uses:
            return False

        if cart_total is not None and self.min_purchase_amount is not None:
            if cart_total < self.min_purchase_amount:
                return False

        return True

    def __str__(self):
        return self.code

class Cart(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

class CartItem(TimeStampedUUIDModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    saved_for_later = models.BooleanField(default=False)

    class Meta:
        unique_together = ("cart", "product")
        ordering = ["-created_at"]
    
    def get_unit_price(self):
        return self.product.get_unit_final_price()

    def get_total_price(self):
        return round(self.get_unit_price() * self.quantity, 2)

class Address(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    country_code = models.CharField(max_length=10, default="+91")
    address_line = models.TextField()
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    address_type = models.CharField(max_length=50, default="home")
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "address_line",
                    "address_line2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                ],
                name="unique_user_address"
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

class Order(TimeStampedUUIDModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        null=False,
        blank=False,
        db_index=True
    )

    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_gateway = models.CharField(
        max_length=20,
        choices=PaymentGateway.choices,
        default=PaymentGateway.RAZORPAY
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True
    )
    payment_reference = models.CharField(max_length=255, blank=True)
    payment_meta = models.JSONField(
        null=True,
        blank=True,
        help_text="Stores complete Razorpay payment response"
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )

    def save(self, *args, **kwargs):
        if not self.order_number:
            with transaction.atomic():
                last_order = Order.objects.select_for_update().order_by("-created_at").first()
                last_number = 0

                if last_order and last_order.order_number:
                    try:
                        last_number = int(last_order.order_number.split("-")[-1])
                    except Exception:
                        last_number = 0

                new_number = last_number + 1
                self.order_number = f"ORD-{str(new_number).zfill(8)}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number}"
    
class OrderItem(TimeStampedUUIDModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

class Wishlist(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wishlist"
    )

    def __str__(self):
        return f"{self.user.email}'s Wishlist"

class WishlistItem(TimeStampedUUIDModel):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlist_entries"
    )

    class Meta:
        unique_together = ("wishlist", "product")

    def __str__(self):
        return f"{self.product.name} in {self.wishlist}"

class Payment(TimeStampedUUIDModel):
    """Model to track Razorpay payment transactions."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED
    )
    failure_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status}"

class Refund(TimeStampedUUIDModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="refunds"
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="refunds"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.REFUND_REQUESTED
    )

    razorpay_refund_id = models.CharField(max_length=100, blank=True, null=True)
    refund_meta = models.JSONField(null=True, blank=True)

    is_partial = models.BooleanField(default=False)
    admin_note = models.TextField(blank=True)

    case_type = models.CharField(
        max_length=50,
        blank=True
    )

class ShopBanner(TimeStampedUUIDModel):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="shop/banners/")
    redirect_category = models.CharField(
        max_length=50,
        choices=ProductCategory.choices,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

class ShopCategoryConfig(TimeStampedUUIDModel):
    category = models.CharField(
        max_length=50,
        choices=ProductCategory.choices,
        unique=True
    )
    image = models.ImageField(upload_to="shop/categories/")
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.category