import uuid
from django.db import models
from rest_framework import serializers
from apps.commerce.models import (
    Product, ProductImage, ProductReview, OrderItem, Cart, CartItem, Address, Coupon, Wishlist, WishlistItem, Order, OrderItem, Payment
)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "created_at"]

class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "tax_percentage", "discount_percentage",
            "images", "category", "brand", "description"
        ]
    
class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "tax_percentage",
            "images", "category", "brand", "description",
            "average_rating", "total_reviews",
        ]
    
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
            "is_active"
        ]

class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code__iexact=value)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code")

        if not coupon.is_valid():
            raise serializers.ValidationError("Coupon is expired or inactive")

        return value

class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.SerializerMethodField()

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

    price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    final_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_image",
            "price",
            "tax_percentage",
            "discount_percentage",
            "final_price",
            "quantity",
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

    def get_final_price(self, obj):
        return obj.get_final_price()

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
            total += item.get_final_price() * item.quantity
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
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_id = serializers.UUIDField(source="product.id", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "quantity",
            "price_at_purchase"
        ]

class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address_summary = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
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
        ]

class AdminProductWriteSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Product
        fields = [
            "name", "category", "brand", "description",
            "price", "tax_percentage", "discount_percentage",
            "is_active", "stock_quantity", "images",
        ]

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        is_out_of_stock = False if validated_data["stock_quantity"] > 0 else True
        validated_data["is_out_of_stock"] = is_out_of_stock
        validated_data["sku"] = uuid.uuid4().hex
        product = Product.objects.create(**validated_data)

        for image in images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def update(self, instance, validated_data):
        images = validated_data.pop("images", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images is not None:
            instance.images.all().delete()
            for image in images:
                ProductImage.objects.create(product=instance, image=image)

        return instance

########### ADMIN ORDER SERIALIZERS ###########

class AdminOrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer for admin with product details."""
    product = serializers.SerializerMethodField()
    final_price = serializers.DecimalField(source="price_at_purchase", max_digits=10, decimal_places=2)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "final_price",
        ]

    def get_product(self, obj):
        product = obj.product
        image_obj = product.images.first()
        image_url = None
        if image_obj and image_obj.image:
            request = self.context.get("request")
            if request:
                image_url = request.build_absolute_uri(image_obj.image.url)
            else:
                image_url = image_obj.image.url

        return {
            "id": str(product.id),
            "name": product.name,
            "image_url": image_url,
            "sku": product.sku,
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
    """Order serializer for admin list view."""
    user = AdminUserSerializer(read_only=True)
    address = AdminAddressSerializer(read_only=True)
    items_count = serializers.SerializerMethodField()
    items = AdminOrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "address",
            "status",
            "total_amount",
            "payment_method",
            "payment_reference",
            "items",
            "items_count",
            "created_at",
            "updated_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()

class AdminOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order serializer for admin detail view."""
    user = AdminUserSerializer(read_only=True)
    address = AdminAddressSerializer(read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "address",
            "status",
            "total_amount",
            "payment_method",
            "payment_reference",
            "items",
            "created_at",
            "updated_at",
        ]

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


class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for verifying Razorpay payment."""
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


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
