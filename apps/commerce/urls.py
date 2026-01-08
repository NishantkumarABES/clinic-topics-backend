from django.urls import path
from apps.commerce.views import (
    ProductListView, ProductDetailView, CartDetailView, AddToCartView, UpdateCartItemView, 
    RemoveCartItemView, AddressListCreateView, AddressDetailView, AdminProductListCreateAPIView, AdminProductUpdateAPIView
)

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<uuid:product_id>/", ProductDetailView.as_view(), name="product-detail"),

    path("cart/", CartDetailView.as_view()),
    path("cart/add/", AddToCartView.as_view()),
    path("cart/item/<uuid:item_id>/", UpdateCartItemView.as_view()),
    path("cart/item/<uuid:item_id>/remove/", RemoveCartItemView.as_view()),

    path("addresses/", AddressListCreateView.as_view()),
    path("addresses/<uuid:address_id>/", AddressDetailView.as_view()),

    path("admin/products/", AdminProductListCreateAPIView.as_view()),
    path("admin/products/<uuid:product_id>/", AdminProductUpdateAPIView.as_view()),
]
