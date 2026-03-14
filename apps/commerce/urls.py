from django.urls import path
from apps.commerce.views import (
    ProductListView, ProductDetailView, CartDetailView, AddToCartView, UpdateCartItemView, RemoveCartItemView, AddressListCreateView, 
    AddressDetailView, AdminProductListCreateAPIView, AdminProductUpdateAPIView, ProductReviewListView, CreateUpdateProductReviewView, 
    ApplyCouponView, RemoveCouponView, AdminCouponListCreateView, AdminCouponUpdateDestroyView, WishlistDetailView, AddToWishlistView, 
    RemoveFromWishlistView, OrderHistoryView, OrderDetailView, ProductFilterOptionsAPIView, ShopLandingAPIView, AdminOrderListAPIView, 
    AdminOrderDetailAPIView, AdminOrderUpdateStatusAPIView, AdminUserAddressListView, CreatePaymentOrderView, VerifyPaymentView, PaymentWebhookView, 
    CancelOrderAPIView, RetryPaymentView, AdminCreateShopCategoryAPIView, UserRefundListView, CreateRefundRequestView, AdminRefundDecisionView,
    AdminRefundListView, AdminBannerListCreateAPIView, AdminBannerUpdateAPIView, AdminBannerDeleteAPIView, AdminProductDetailAPIView
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
    path("orders/<uuid:order_id>/cancel/", CancelOrderAPIView.as_view()),
    path("orders/<uuid:order_id>/refund/", CreateRefundRequestView.as_view()),
    path("orders/<uuid:order_id>/retry-payment/", RetryPaymentView.as_view()),
    path("orders/refunds/", UserRefundListView.as_view()),

    # Payment endpoints
    path("payment/create-order/", CreatePaymentOrderView.as_view(), name="payment-create-order"),
    path("payment/verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("payment/webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    
    path("admin/products/", AdminProductListCreateAPIView.as_view()),
    path("admin/products/<uuid:product_id>/", AdminProductUpdateAPIView.as_view()),
    path("admin/products/<uuid:product_id>/details/", AdminProductDetailAPIView.as_view()),
    path("admin/coupons/", AdminCouponListCreateView.as_view()),
    path("admin/coupons/<uuid:coupon_id>/", AdminCouponUpdateDestroyView.as_view()),

    # Admin Order endpoints
    path("admin/orders/", AdminOrderListAPIView.as_view(), name="admin-order-list"),
    path("admin/orders/<uuid:order_id>/", AdminOrderDetailAPIView.as_view(), name="admin-order-detail"),
    path("admin/orders/<uuid:order_id>/status/", AdminOrderUpdateStatusAPIView.as_view(), name="admin-order-status"),
    path("admin/banners/", AdminBannerListCreateAPIView.as_view(), name="admin-create-banner"),
    path("admin/banners/<uuid:banner_id>/", AdminBannerUpdateAPIView.as_view(), name="admin-update-banner"),
    path("admin/banners/<uuid:banner_id>/delete/", AdminBannerDeleteAPIView.as_view(), name="admin-delete-banner"),
    path("admin/categories/", AdminCreateShopCategoryAPIView.as_view(), name="admin-create-category"),
    path("admin/refunds/", AdminRefundListView.as_view(), name="admin-refund-list"),
    path("admin/refunds/<uuid:refund_id>/decision/", AdminRefundDecisionView.as_view(), name="admin-refund-decision"),
    
    # Admin user addresses endpoint
    path("admin/users/<uuid:user_id>/addresses/", AdminUserAddressListView.as_view(), name="admin-user-addresses"),
]
