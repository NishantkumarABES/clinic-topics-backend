import uuid
from decimal import Decimal
from django.db import models, transaction
from django.db.models import Sum, F
from rest_framework import serializers
from apps.commerce.models import (
    Product, ProductImage, ProductReview, OrderItem, Cart, CartItem, Address, Coupon, Wishlist, WishlistItem, Order, OrderItem, Payment,
    ShopBanner, ShopCategoryConfig, Refund
)
from apps.commerce.constants import OrderStatus, PaymentStatus, RefundStatus


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "created_at"]

class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    base_price = serializers.DecimalField(source="price", max_digits=10, decimal_places=2, read_only=True)
    tax_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "base_price", "tax_percentage", "discount_percentage", "final_price",
            "images", "category", "brand", "description", "for_patients", "for_doctors"
        ]
    def get_final_price(self, obj):
        return obj.get_unit_final_price()
    
class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    base_price = serializers.DecimalField(source="price", max_digits=10, decimal_places=2, read_only=True)
    tax_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    final_price = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "base_price", "tax_percentage", "discount_percentage", "final_price",
            "images", "category", "brand", "description", "average_rating", "total_reviews", "for_patients", 
            "for_doctors"
        ]
    
    def get_final_price(self, obj):
        return obj.get_unit_final_price()
    
    def get_average_rating(self, obj):
        agg = obj.reviews.aggregate(avg=models.Avg("rating"))
        return round(agg["avg"] or 0, 2)

    def get_total_reviews(self, obj):
        return obj.reviews.count()

class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "user_name",
            "rating",
            "comment",
            "is_verified_purchase",
            "created_at",
        ]

class CreateUpdateReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProductReview
        fields = ["product_id", "rating", "comment"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        product_id = validated_data.pop("product_id")

        # check verified purchase
        verified = OrderItem.objects.filter(
            order__user=user,
            product_id=product_id
        ).exists()

        review, _ = ProductReview.objects.update_or_create(
            user=user,
            product_id=product_id,
            defaults={
                "rating": validated_data["rating"],
                "comment": validated_data.get("comment", ""),
                "is_verified_purchase": verified
            }
        )
        return review

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_purchase_amount",
            "max_discount_amount",
            "max_uses",
            "current_uses",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at",
            "updated_at",
        ]

class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate(self, attrs):
        code = attrs.get("code")

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid coupon code"})

        if not coupon.is_valid():
            raise serializers.ValidationError(
                {"code": "Coupon is expired or inactive"}
            )

        # Attach coupon so view doesn't query again
        attrs["coupon"] = coupon
        return attrs

class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    brand = serializers.CharField(source="product.brand", read_only=True)
    category_name = serializers.CharField(source="product.category", read_only=True)
    product_image = serializers.SerializerMethodField()
    base_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    tax_percentage = serializers.DecimalField(source="product.tax_percentage", max_digits=5, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(source="product.discount_percentage", max_digits=5, decimal_places=2, read_only=True)
    final_price = serializers.SerializerMethodField()
    final_total = serializers.SerializerMethodField()

    
    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "brand",
            "category_name",
            "product_image",
            "base_price",
            "tax_percentage",
            "discount_percentage",
            "final_price",
            "quantity",
            "final_total",
            "saved_for_later",
        ]
    
    def get_product_image(self, obj):
        image_obj = obj.product.images.first()
        if not image_obj or not image_obj.image:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(image_obj.image.url)

        return image_obj.image.url
    
    def get_final_total(self, obj):
        return round(obj.product.get_unit_final_price() * obj.quantity, 2)

    def get_final_price(self, obj):
        return obj.product.get_unit_final_price()

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    applied_coupon = serializers.CharField(source="coupon.code", read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_amount",
            "discount",
            "final_amount",
            "applied_coupon"
        ]

    def get_total_amount(self, obj):
        total = 0
        for item in obj.items.filter(saved_for_later=False):
            total += item.product.get_unit_final_price() * item.quantity
        return round(total, 2)

    def get_discount(self, obj):
        if not obj.coupon:
            return 0

        coupon = obj.coupon
        total = self.get_total_amount(obj)

        # Recheck validity
        if not coupon.is_valid(cart_total=total):
            return 0

        # Calculate discount
        if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
            discount = total * (coupon.discount_value / 100)
        else:
            discount = coupon.discount_value

        # Apply max discount cap if set
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)

        return round(discount, 2)

    def get_final_amount(self, obj):
        total = self.get_total_amount(obj)
        discount = self.get_discount(obj)
        return round(total - discount, 2)

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid product")
        return value

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ("user",)

class AddressCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "name",
            "phone",
            "country_code",
            "address_line",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "address_type",
            "is_default",
        ]

class AddressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "name",
            "phone",
            "country_code",
            "address_line",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "address_type",
            "is_default",
        ]

class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "created_at"]

class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "items"]

class AddToWishlistSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_image = serializers.SerializerMethodField()
    product_name = serializers.CharField(source="product.name", read_only=True)
    base_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    tax_percentage = serializers.DecimalField(source="product.tax_percentage", max_digits=5, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(source="product.discount_percentage", max_digits=5, decimal_places=2, read_only=True)

    final_price = serializers.DecimalField(source="price_at_purchase", max_digits=10, decimal_places=2, read_only=True)
    final_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_image",
            "base_price",
            "tax_percentage",
            "discount_percentage",
            "final_price",
            "quantity",
            "final_total"
        ]
    
    def get_final_total(self, obj):
        return round(obj.price_at_purchase * obj.quantity, 2)
    
    def get_product_image(self, obj):
        product = obj.product
        if not product:
            return None

        first_image = product.images.first()
        if not first_image or not first_image.image:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(first_image.image.url)

        return first_image.image.url

class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address_summary = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "total_amount",
            "payment_method",
            "payment_reference",
            "created_at",
            "address_summary",
            "items"
        ]

    def get_address_summary(self, obj):
        addr = obj.address
        return f"{addr.address_line}, {addr.city}, {addr.state}, {addr.postal_code}"

class ShopBannerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ShopBanner
        fields = ["id", "title", "subtitle", "image", "redirect_category", "is_active", "order"]

    def get_image(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class ShopCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ShopCategoryConfig
        fields = [
            "id",
            "category",
            "image",
            "title",
            "subtitle",
            "product_count"
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_product_count(self, obj):
        return Product.objects.filter(
            category=obj.category,
            is_active=True,
            stock_quantity__gt=0
        ).count()

class RefundRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        order = self.context["order"]

        # Order must belong to user
        if order.user != request.user:
            raise serializers.ValidationError("Invalid order.")

        # Order must be eligible for refund
        if order.status not in [
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
        ]:
            raise serializers.ValidationError(
                "Refund not allowed for this order status."
            )

        # Get successful payment
        payment = order.payments.filter(
            status=PaymentStatus.CAPTURED
        ).first()

        if not payment:
            raise serializers.ValidationError(
                "No successful payment found for this order."
            )

        # Calculate already refunded amount
        refunded_total = order.refunds.filter(
            status=RefundStatus.REFUND_COMPLETED
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        refundable_balance = payment.amount - refunded_total

        if refundable_balance <= 0:
            raise serializers.ValidationError(
                "No refundable balance remaining for this order."
            )

        attrs["payment"] = payment
        attrs["refund_amount"] = refundable_balance

        return attrs

class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id",
            "amount",
            "reason",
            "status",
            "is_partial",
            "razorpay_refund_id",
            "created_at",
            "updated_at",
        ]

class AdminRefundDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    admin_note = serializers.CharField(required=False, allow_blank=True)

########### ADMIN SERIALIZERS ###########
class AdminProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "created_at"]

class AdminProductReadSerializer(serializers.ModelSerializer):
    images = AdminProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "category", "brand",
            "description", "price", "tax_percentage", "discount_percentage",
            "is_active", "stock_quantity", "images", "created_at", "updated_at",
            "for_patients", "for_doctors"
        ]

class AdminProductWriteSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )
    deleted_image_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Product
        fields = [
            "name", "category", "brand", "description",
            "price", "tax_percentage", "discount_percentage",
            "is_active", "stock_quantity", "images", "deleted_image_ids",
            "for_patients", "for_doctors"
        ]

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        validated_data.pop("deleted_image_ids", None)
        validated_data["sku"] = uuid.uuid4().hex
        product = Product.objects.create(**validated_data)

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def update(self, instance, validated_data):
        images = validated_data.pop("images", None)
        deleted_image_ids = validated_data.pop("deleted_image_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Delete only specific images if requested
        if deleted_image_ids:
            instance.images.filter(id__in=deleted_image_ids).delete()

        # Append new images (don't replace existing)
        if images:
            for image in images:
                ProductImage.objects.create(product=instance, image=image)

        return instance

class AdminShopCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopCategoryConfig
        fields = [
            "category",
            "image",
            "title",
            "subtitle",
            "is_active",
            "order",
        ]

    def validate_category(self, value):
        if ShopCategoryConfig.objects.filter(category=value).exists():
            raise serializers.ValidationError("Category already configured.")
        return value

class AdminShopBannerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopBanner
        fields = [
            "title",
            "subtitle",
            "image",
            "redirect_category",
            "is_active",
            "order",
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        order = validated_data.get("order", 0)
        is_active = validated_data.get("is_active", True)

        if is_active and order:
            ShopBanner.objects.filter(
                order__gte=order,
                is_active=True
            ).update(order=F("order") + 1)

        banner = ShopBanner.objects.create(**validated_data)
        return banner
    
    @transaction.atomic
    def update(self, instance, validated_data):
        new_order = validated_data.get("order", instance.order)
        old_order = instance.order

        if new_order != old_order:

            if new_order < old_order:
                ShopBanner.objects.filter(
                    order__gte=new_order,
                    order__lt=old_order,
                    is_active=True
                ).update(order=F("order") + 1)

            else:
                ShopBanner.objects.filter(
                    order__gt=old_order,
                    order__lte=new_order,
                    is_active=True
                ).update(order=F("order") - 1)

        return super().update(instance, validated_data)

########### ADMIN ORDER SERIALIZERS ###########
class AdminOrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer for admin with full pricing details."""

    product = serializers.SerializerMethodField()

    # Pricing breakdown
    base_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    tax_percentage = serializers.DecimalField(
        source="product.tax_percentage",
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    discount_percentage = serializers.DecimalField(
        source="product.discount_percentage",
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    final_price = serializers.DecimalField(
        source="price_at_purchase",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    final_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "base_price",
            "tax_percentage",
            "discount_percentage",
            "final_price",
            "quantity",
            "final_total",
        ]

    def get_final_total(self, obj):
        return round(obj.price_at_purchase * obj.quantity, 2)

    def get_product(self, obj):
        product = obj.product
        image_obj = product.images.first()
        image_url = None

        if image_obj and image_obj.image:
            request = self.context.get("request")
            image_url = (
                request.build_absolute_uri(image_obj.image.url)
                if request else image_obj.image.url
            )

        return {
            "id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "image_url": image_url,
        }

class AdminAddressSerializer(serializers.ModelSerializer):
    """Address serializer for admin order views."""

    class Meta:
        model = Address
        fields = [
            "name",
            "phone",
            "address_line",
            "city",
            "state",
            "postal_code",
            "country",
        ]

class AdminUserSerializer(serializers.Serializer):
    """User serializer for admin order views."""
    id = serializers.UUIDField()
    name = serializers.CharField(source="full_name")
    email = serializers.EmailField()
    phone = serializers.SerializerMethodField()

    def get_phone(self, obj):
        return getattr(obj, "phone", None)

class AdminOrderListSerializer(serializers.ModelSerializer):
    user = AdminUserSerializer(read_only=True)
    address = AdminAddressSerializer(read_only=True)
    items_count = serializers.SerializerMethodField()
    items = AdminOrderItemSerializer(many=True, read_only=True)
    subtotal_amount = serializers.SerializerMethodField()
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)
    coupon_discount = serializers.SerializerMethodField()
    coupon_type = serializers.CharField(source="coupon.discount_type", read_only=True)
    coupon_value = serializers.DecimalField(
        source="coupon.discount_value",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "user",
            "address",
            "status",
            "subtotal_amount",
            "coupon_code",
            "coupon_type",
            "coupon_value",
            "coupon_discount",
            "total_amount",
            "payment_method",
            "payment_reference",
            "payment_meta",
            "items",
            "items_count",
            "created_at",
            "updated_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_subtotal_amount(self, obj):
        subtotal = 0
        for item in obj.items.all():
            subtotal += item.price_at_purchase * item.quantity
        return round(subtotal, 2)

    def get_coupon_discount(self, obj):
        if not obj.coupon:
            return 0

        subtotal = self.get_subtotal_amount(obj)

        # Discount = subtotal - final total
        discount = subtotal - obj.total_amount

        if discount < 0:
            discount = 0

        return round(discount, 2)

class AdminOrderDetailSerializer(serializers.ModelSerializer):
    user = AdminUserSerializer(read_only=True)
    address = AdminAddressSerializer(read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)

    subtotal_amount = serializers.SerializerMethodField()
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)
    coupon_discount = serializers.SerializerMethodField()
    coupon_type = serializers.CharField(source="coupon.discount_type", read_only=True)
    coupon_value = serializers.DecimalField(
        source="coupon.discount_value",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "user",
            "address",
            "status",
            "subtotal_amount",
            "coupon_code",
            "coupon_type",
            "coupon_value",
            "coupon_discount",
            "total_amount",
            "payment_method",
            "payment_reference",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_subtotal_amount(self, obj):
        subtotal = 0
        for item in obj.items.all():
            subtotal += item.price_at_purchase * item.quantity
        return round(subtotal, 2)

    def get_coupon_discount(self, obj):
        if not obj.coupon:
            return 0

        subtotal = self.get_subtotal_amount(obj)
        discount = subtotal - obj.total_amount

        if discount < 0:
            discount = 0

        return round(discount, 2)

class UpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for updating order status."""
    status = serializers.ChoiceField(choices=[
        "pending_payment", "paid", "processing", 
        "shipped", "delivered", "cancelled", "refunded"
    ])
    note = serializers.CharField(required=False, allow_blank=True)

class AdminCreateOrderItemSerializer(serializers.Serializer):
    """Serializer for order items when creating an order."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

class AdminCreateOrderSerializer(serializers.Serializer):
    """Serializer for admin manual order creation."""
    user_id = serializers.UUIDField()
    address_id = serializers.UUIDField()
    items = AdminCreateOrderItemSerializer(many=True, min_length=1)
    payment_method = serializers.ChoiceField(choices=[
        "card", "upi", "netbanking", "wallet", "cod"
    ])
    payment_reference = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=["pending_payment", "paid", "processing", "shipped", "delivered", "cancelled", "refunded"],
        default="pending_payment"
    )

    def validate_user_id(self, value):
        from apps.accounts.models import User
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found")
        return value

    def validate_address_id(self, value):
        if not Address.objects.filter(id=value).exists():
            raise serializers.ValidationError("Address not found")
        return value

    def validate_items(self, value):
        for item in value:
            if not Product.objects.filter(id=item["product_id"]).exists():
                raise serializers.ValidationError(f"Product {item['product_id']} not found")
        return value


########### PAYMENT SERIALIZERS ###########

class CreatePaymentOrderSerializer(serializers.Serializer):
    """Serializer for creating a Razorpay order."""
    address_id = serializers.UUIDField()

    def validate_address_id(self, value):
        request = self.context.get("request")
        if not Address.objects.filter(id=value, user=request.user).exists():
            raise serializers.ValidationError("Address not found")
        return value
    
    class Meta:
        ref_name = "CommerceCreatePaymentOrderSerializer"

class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for verifying Razorpay payment."""
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

    class Meta:
        ref_name = "CommerceVerifyPaymentSerializer"

class PaymentSerializer(serializers.ModelSerializer):
    """Read serializer for Payment model."""
    order_id = serializers.UUIDField(source="order.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_id",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount",
            "currency",
            "status",
            "created_at",
        ]

class RetryPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()

#########################   Response Serializers    #########################

class StandardResponseSerializer(serializers.Serializer):
    """Standard response wrapper for simple responses."""
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False, help_text="Response data")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "CommerceStandardResponseSerializer"


# Product response serializers
class ProductDetailResponseSerializer(serializers.Serializer):
    """Response for product detail endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = ProductDetailSerializer()
    success = serializers.BooleanField(help_text="Success status")

class ProductReviewListResponseSerializer(serializers.Serializer):
    """Response for product review list endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = ProductReviewSerializer(many=True)
    success = serializers.BooleanField(help_text="Success status")

class ProductReviewResponseSerializer(serializers.Serializer):
    """Response for create/update product review endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = ProductReviewSerializer()
    success = serializers.BooleanField(help_text="Success status")


# Cart response serializers
class CartResponseSerializer(serializers.Serializer):
    """Response for cart detail endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = CartSerializer()
    success = serializers.BooleanField(help_text="Success status")

# Address response serializers
class AddressListResponseSerializer(serializers.Serializer):
    """Response for address list endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = AddressSerializer(many=True)
    success = serializers.BooleanField(help_text="Success status")

class AddressResponseSerializer(serializers.Serializer):
    """Response for single address endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = AddressSerializer()
    success = serializers.BooleanField(help_text="Success status")

# Wishlist response serializers
class WishlistResponseSerializer(serializers.Serializer):
    """Response for wishlist detail endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = WishlistSerializer()
    success = serializers.BooleanField(help_text="Success status")


# Order response serializers
class OrderDetailResponseSerializer(serializers.Serializer):
    """Response for order detail endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = OrderHistorySerializer()
    success = serializers.BooleanField(help_text="Success status")

class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

# class RefundRequestSerializer(serializers.Serializer):
#     reason = serializers.CharField(required=False, allow_blank=True)
