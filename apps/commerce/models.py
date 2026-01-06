from django.db import models
from core.models import TimeStampedUUIDModel

from apps.accounts.models import User
from apps.commerce.constants import ProductCategory


class Prescription(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )

    file = models.FileField(upload_to="prescriptions/")
    notes = models.TextField(blank=True)

    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Prescription({self.user.full_name})"

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

class Product(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    # SKU stands for Stock Keeping Unit, a unique identifier for each product in inventory.

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        choices=ProductCategory.CHOICES
    )

    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_prescription_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    stock_quantity = models.PositiveIntegerField(default=0)

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

class Cart(TimeStampedUUIDModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
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

    prescription = models.ForeignKey(
        Prescription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

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

    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.city}"

class Order(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
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


