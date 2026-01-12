import uuid
from django.db import models
from rest_framework import serializers
from apps.commerce.models import (
    Product, ProductImage, ProductReview, OrderItem, Cart, CartItem, Address, Coupon, Wishlist, WishlistItem
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
            "discount_percentage",
            "discount_amount",
            "minimum_cart_amount",
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
        fields = ["id", "items", "total_amount", "discount", "final_amount", "applied_coupon"]

    def get_total_amount(self, obj):
        total = 0
        for item in obj.items.filter(saved_for_later=False):
            total += item.get_final_price() * item.quantity
        return round(total, 2)

    def get_discount(self, obj):
        if not obj.coupon:
            return 0

        total = self.get_total_amount(obj)
        coupon = obj.coupon

        if total < coupon.minimum_cart_amount:
            return 0

        if coupon.discount_percentage:
            return round(total * (coupon.discount_percentage / 100), 2)

        if coupon.discount_amount:
            return min(coupon.discount_amount, total)

        return 0

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

class AddressUpdateSerializer(AddressCreateSerializer):
    pass



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