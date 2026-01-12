from django.db import models
from core.models import TimeStampedUUIDModel
from decimal import Decimal

from apps.accounts.models import User
from apps.commerce.constants import ProductCategory
from apps.commerce.constants import OrderStatus


class Product(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    # SKU stands for Stock Keeping Unit, a unique identifier for each product in inventory.

    category = models.CharField(
        max_length=50,
        choices=ProductCategory.CHOICES
    )
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)
    is_out_of_stock = models.BooleanField(default=False)
    stock_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "brand"],
                name="unique_product_name_brand"
            )
        ]

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
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    minimum_cart_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    max_usage = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()

        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.used_count >= self.max_usage:
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
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    saved_for_later = models.BooleanField(default=False)

    def get_final_price(self):
        price = self.product.price

        if self.product.discount_percentage > 0:
            price -= (price * self.product.discount_percentage / Decimal("100"))

        tax = price * (self.product.tax_percentage / Decimal("100"))
        return round(price + tax, 2)

    class Meta:
        unique_together = ("cart", "product")

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

    status = models.CharField(max_length=20, choices=OrderStatus.CHOICES)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=50)
    payment_reference = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Order {self.id}"

class OrderItem(TimeStampedUUIDModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

class Category(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children"
    )

    def __str__(self):
        return self.name


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
