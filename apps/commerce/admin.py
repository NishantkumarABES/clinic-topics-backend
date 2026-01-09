from django.contrib import admin
from apps.commerce.models import Category, Product, ProductImage, Address, Cart, CartItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "price", "stock_quantity", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku")
    inlines = [ProductImageInline]



@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "is_default")
    list_filter = ("city",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    inlines = [CartItemInline]

