from django.urls import path
from apps.commerce.views import (
    ProductListView, ProductDetailView, CartDetailView, AddToCartView, UpdateCartItemView, RemoveCartItemView, AddressListCreateView, 
    AddressDetailView, AdminProductListCreateAPIView, AdminProductUpdateAPIView, ProductReviewListView, CreateUpdateProductReviewView, 
    ApplyCouponView, RemoveCouponView, AdminCouponListCreateView, AdminCouponUpdateDestroyView, WishlistDetailView, AddToWishlistView, 
    RemoveFromWishlistView, OrderHistoryView, OrderDetailView, ProductFilterOptionsAPIView, ShopLandingAPIView,
    AdminOrderListAPIView, AdminOrderDetailAPIView, AdminOrderUpdateStatusAPIView, AdminUserAddressListView,
    CreatePaymentOrderView, VerifyPaymentView, PaymentWebhookView, CancelOrderView, RefundOrderView, RetryPaymentView,
    AdminCreateShopBannerAPIView, AdminCreateShopCategoryAPIView
)

urlpatterns = [
    path("landing/", ShopLandingAPIView.as_view(), name="shop-landing"),

    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<uuid:product_id>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/<uuid:product_id>/reviews/", ProductReviewListView.as_view()),
    path("products/review/", CreateUpdateProductReviewView.as_view()),
    path("products/filter-options/", ProductFilterOptionsAPIView.as_view()),

    path("cart/", CartDetailView.as_view()),
    path("cart/add/", AddToCartView.as_view()),
    path("cart/item/<uuid:item_id>/", UpdateCartItemView.as_view()),
    path("cart/item/<uuid:item_id>/remove/", RemoveCartItemView.as_view()),
    path("cart/apply-coupon/", ApplyCouponView.as_view()),
    path("cart/remove-coupon/", RemoveCouponView.as_view()),

    path("addresses/", AddressListCreateView.as_view()),
    path("addresses/<uuid:address_id>/", AddressDetailView.as_view()),

    path("wishlist/", WishlistDetailView.as_view()),
    path("wishlist/add/", AddToWishlistView.as_view()),
    path("wishlist/remove/<uuid:item_id>/", RemoveFromWishlistView.as_view()),

    path("orders/", OrderHistoryView.as_view()),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view()),
    path("orders/<uuid:order_id>/cancel/", CancelOrderView.as_view()),
    path("orders/<uuid:order_id>/refund/", RefundOrderView.as_view()),
    path("orders/<uuid:order_id>/retry-payment/", RetryPaymentView.as_view()),

    # Payment endpoints
    path("payment/create-order/", CreatePaymentOrderView.as_view(), name="payment-create-order"),
    path("payment/verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("payment/webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),

    path("admin/products/", AdminProductListCreateAPIView.as_view()),
    path("admin/products/<uuid:product_id>/", AdminProductUpdateAPIView.as_view()),
    path("admin/coupons/", AdminCouponListCreateView.as_view()),
    path("admin/coupons/<uuid:coupon_id>/", AdminCouponUpdateDestroyView.as_view()),

    # Admin Order endpoints
    path("admin/orders/", AdminOrderListAPIView.as_view(), name="admin-order-list"),
    path("admin/orders/<uuid:order_id>/", AdminOrderDetailAPIView.as_view(), name="admin-order-detail"),
    path("admin/orders/<uuid:order_id>/status/", AdminOrderUpdateStatusAPIView.as_view(), name="admin-order-status"),
    path("admin/banners/", AdminCreateShopBannerAPIView.as_view(), name="admin-create-banner"),
    path("admin/categories/", AdminCreateShopCategoryAPIView.as_view(), name="admin-create-category"),
    
    # Admin user addresses endpoint
    path("admin/users/<uuid:user_id>/addresses/", AdminUserAddressListView.as_view(), name="admin-user-addresses"),
]
