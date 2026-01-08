import uuid
from rest_framework import serializers
from apps.commerce.models import Product, ProductImage, Cart, CartItem, Address, Prescription



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
            "images", "category", "brand", "description",
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "tax_percentage",
            "images", "category", "brand", "description",
        ]

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "price",
            "quantity",
            "saved_for_later",
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_amount"]

    def get_total_amount(self, obj):
        total = 0
        for item in obj.items.filter(saved_for_later=False):
            price = item.product.price
            tax = price * (item.product.tax_percentage / 100)
            total += (price + tax) * item.quantity
        return round(total, 2)

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

class AttachPrescriptionSerializer(serializers.Serializer):
    cart_item_id = serializers.UUIDField()
    prescription_id = serializers.UUIDField()




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