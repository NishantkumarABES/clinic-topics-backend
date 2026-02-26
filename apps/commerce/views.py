import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum, Min, Max
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal


from core.permissions import IsAdmin
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404
from apps.accounts.models import UserRole
from apps.commerce.models import Product, Cart, CartItem, Address, Coupon, ProductReview, Wishlist, WishlistItem, Order, OrderItem, Payment
from apps.commerce.models import PaymentStatus, ShopCategoryConfig, ShopBanner
from apps.commerce.serializers import (
    ProductListSerializer, ProductDetailSerializer, CartSerializer, AddToCartSerializer, AddressSerializer,
    AddressCreateSerializer, AddressUpdateSerializer, AdminProductReadSerializer, AdminProductWriteSerializer,
    ProductReviewSerializer, CreateUpdateReviewSerializer, ApplyCouponSerializer, CouponSerializer,
    WishlistSerializer, AddToWishlistSerializer, WishlistItem, OrderHistorySerializer,
    AdminOrderListSerializer, AdminOrderDetailSerializer, UpdateOrderStatusSerializer, AdminCreateOrderSerializer,
    CreatePaymentOrderSerializer, VerifyPaymentSerializer, CancelOrderSerializer, RefundRequestSerializer,
    ShopCategorySerializer, ShopBannerSerializer, AdminShopBannerWriteSerializer, AdminShopCategoryWriteSerializer,
    # Response serializers
    StandardResponseSerializer, ProductDetailResponseSerializer, ProductReviewListResponseSerializer,
    ProductReviewResponseSerializer, CartResponseSerializer, AddressListResponseSerializer,
    AddressResponseSerializer, WishlistResponseSerializer, OrderDetailResponseSerializer
)
from apps.commerce.constants import OrderStatus, ProductCategory
from apps.notifications.services import create_admin_notification
from external.razorpay.service import razorpay_service

class ShopLandingAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id="shop_landing",
        operation_description="Returns shop landing categories and banners",
        tags=["Commerce - Shop"]
    )
    def get(self, request):

        categories = ShopCategoryConfig.objects.filter(
            is_active=True
        )

        banners = ShopBanner.objects.filter(
            is_active=True
        )

        return Response({
            "success": True,
            "detail": "Shop landing data fetched successfully",
            "data": {
                "categories": ShopCategorySerializer(
                    categories,
                    many=True,
                    context={"request": request}
                ).data,
                "banners": ShopBannerSerializer(
                    banners,
                    many=True,
                    context={"request": request}
                ).data
            }
        })

class ProductListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = ProductListPagination
    
    @swagger_auto_schema(
        operation_id="list_products",
        operation_description="List all products with optional filters for category, search, price range, and brand. Returns paginated results.",
        tags=["Commerce - Products"],
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, description="Filter by product category", type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search products by name", type=openapi.TYPE_STRING),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price filter", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price filter", type=openapi.TYPE_NUMBER),
            openapi.Parameter('brand', openapi.IN_QUERY, description="Filter by brand name", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number for pagination", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page (max 100)", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ProductListSerializer(many=True)}
    )
    def get(self, request):
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        min_price = request.query_params.get("min_price", 0)
        max_price = request.query_params.get("max_price", 999999999)
        brand = request.query_params.get("brand")
        user = request.user

        queryset = Product.objects.filter(stock_quantity__gt=0)
        if user.role == UserRole.DOCTOR:
            queryset = queryset.filter(for_doctors=True)

        elif user.role == UserRole.PATIENT:
            queryset = queryset.filter(for_patients=True)

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        if category:
            queryset = queryset.filter(category=category)
        
        if brand:
            queryset = queryset.filter(brand=brand)

        if search:
            queryset = queryset.filter(name__icontains=search)

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = ProductListSerializer(paginated_queryset, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail" : "",
            "success" : True,
            "data" : response_data
        })

class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id="get_product_detail",
        operation_description="Get detailed information about a specific product including images, rating, and reviews count.",
        tags=["Commerce - Products"],
        responses={
            200: ProductDetailResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found", "data": None, "success": False},
                status=404
            )

        serializer = ProductDetailSerializer(product)
        return Response({
            "detail": "Product retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class ProductReviewListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id="list_product_reviews",
        operation_description="Get all reviews for a specific product, ordered by most recent first.",
        tags=["Commerce - Products"],
        responses={200: ProductReviewListResponseSerializer()}
    )
    def get(self, request, product_id):
        reviews = ProductReview.objects.filter(product_id=product_id).order_by("-created_at")
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response({
            "detail": "Reviews retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class ProductFilterOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="product_filter_options",
        operation_description="Get filter options including categories, brands, brands by category, and price ranges.",
        tags=["Commerce - Products"],
        responses={
            200: openapi.Response(
                description="Filter options retrieved successfully"
            )
        }
    )
    def get(self, request):
        user = request.user

        # Base queryset (only active and in stock)
        queryset = Product.objects.filter(
            is_active=True,
            stock_quantity__gt=0
        )

        # Role-based filtering
        if user.role == UserRole.DOCTOR:
            queryset = queryset.filter(for_doctors=True)
        elif user.role == UserRole.PATIENT:
            queryset = queryset.filter(for_patients=True)

        # -----------------------------------
        # 1️⃣ Categories
        # -----------------------------------
        categories = [
            label for value, label in ProductCategory.CHOICES
        ]

        # -----------------------------------
        # 2️⃣ Global Brands
        # -----------------------------------
        brands = (
            queryset.exclude(brand="")
            .values_list("brand", flat=True)
            .distinct()
            .order_by("brand")
        )

        # -----------------------------------
        # 3️⃣ Brands by Category
        # -----------------------------------
        brands_by_category = {}

        for category_value, _ in ProductCategory.CHOICES:
            category_brands = (
                queryset.filter(category=category_value)
                .exclude(brand="")
                .values_list("brand", flat=True)
                .distinct()
                .order_by("brand")
            )
            brands_by_category[category_value] = list(category_brands)

        # -----------------------------------
        # 4️⃣ Global Price Range
        # -----------------------------------
        price_agg = queryset.aggregate(
            min_price=Min("price"),
            max_price=Max("price")
        )

        price_range = {
            "min_price": price_agg["min_price"] or 0,
            "max_price": price_agg["max_price"] or 0,
        }

        # -----------------------------------
        # 5️⃣ Price Range by Category
        # -----------------------------------
        price_range_by_category = {}

        for category_value, _ in ProductCategory.CHOICES:
            category_queryset = queryset.filter(category=category_value)

            agg = category_queryset.aggregate(
                min_price=Min("price"),
                max_price=Max("price")
            )

            price_range_by_category[category_value] = {
                "min_price": agg["min_price"] or 0,
                "max_price": agg["max_price"] or 0,
            }

        return Response({
            "success": True,
            "detail": "Filter options fetched successfully",
            "data": {
                "categories": categories,
                "brands": list(brands),
                "brands_by_category": brands_by_category,
                "price_range": price_range,
                "price_range_by_category": price_range_by_category,
            }
        })

class CreateUpdateProductReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="create_update_review",
        operation_description="Create a new review or update an existing one for a product. Automatically marks as verified purchase if user has ordered the product.",
        tags=["Commerce - Products"],
        request_body=CreateUpdateReviewSerializer,
        responses={
            200: ProductReviewResponseSerializer(),
            400: BAD_REQUEST_400
        }
    )
    def post(self, request):
        serializer = CreateUpdateReviewSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as E:
            return Response({"detail": str(E), "data": None, "success": False})

        review = serializer.save()
        return Response({
            "detail": "Review saved successfully",
            "data": ProductReviewSerializer(review).data,
            "success": True
        })

class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="apply_coupon",
        operation_description="Apply a coupon code to the user's cart. Validates coupon eligibility based on cart total and coupon rules.",
        tags=["Commerce - Cart"],
        request_body=ApplyCouponSerializer,
        responses={
            200: StandardResponseSerializer(),
            400: BAD_REQUEST_400
        }
    )
    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.validated_data["coupon"]

        # Get cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Calculate cart total
        total = sum(
            item.get_total_price()
            for item in cart.items.filter(saved_for_later=False)
        ).quantize(Decimal("0.01"))

        # Validate coupon against cart total
        if not coupon.is_valid(cart_total=total):
            return Response(
                {
                    "detail": "Coupon is not valid for this cart",
                    "data": None,
                    "success": False,
                },
                status=400,
            )

        cart.coupon = coupon
        cart.save(update_fields=["coupon"])

        return Response(
            {
                "detail": "Coupon applied successfully",
                "data": None,
                "success": True,
            },
            status=200,
        )

class RemoveCouponView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="remove_coupon",
        operation_description="Remove any applied coupon from the user's cart.",
        tags=["Commerce - Cart"],
        responses={200: StandardResponseSerializer()}
    )
    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.coupon = None
        cart.save(update_fields=["coupon"])
        return Response({
            "detail": "Coupon removed",
            "data": None,
            "success": True
        })

class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="get_cart",
        operation_description="Get the current user's cart with all items, applied coupon, and calculated totals including discounts.",
        tags=["Commerce - Cart"],
        responses={200: CartResponseSerializer()}
    )
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response({
            "detail": "Cart retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_id="add_to_cart",
        operation_description="Add a product to the cart. If the product already exists, the quantity is incremented.",
        tags=["Commerce - Cart"],
        request_body=AddToCartSerializer(),
        responses={
            201: StandardResponseSerializer(),
            400: BAD_REQUEST_400
        }
    )
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        product = Product.objects.get(id=serializer.validated_data["product_id"])
        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity"])

        return Response({"detail": "Item added to cart", "data": None, "success": True}, status=201)

class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="update_cart_item",
        operation_description="Update cart item quantity or save for later status. Setting quantity to 0 or less removes the item.",
        tags=["Commerce - Cart"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='New quantity (0 or less removes item)'),
                'saved_for_later': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Save item for later')
            }
        ),
        responses={
            200: StandardResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def patch(self, request, item_id):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({"detail": "Item not found", "data": None, "success": False}, status=404)

        quantity = request.data.get("quantity")
        saved_for_later = request.data.get("saved_for_later")

        if quantity is not None:
            if quantity <= 0:
                item.delete()
                return Response({"detail": "Item removed", "data": None, "success": True})
            item.quantity = quantity

        if saved_for_later is not None:
            item.saved_for_later = saved_for_later

        item.save()
        return Response({"detail": "Cart updated", "data": None, "success": True})

class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="remove_cart_item",
        operation_description="Remove an item from the cart.",
        tags=["Commerce - Cart"],
        responses={200: StandardResponseSerializer()}
    )
    def delete(self, request, item_id):
        CartItem.objects.filter(
            id=item_id, cart__user=request.user
        ).delete()
        return Response({"detail": "Item removed", "data": None, "success": True})

class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="list_addresses",
        operation_description="List all addresses for the current user, ordered by default status and creation date.",
        tags=["Commerce - Address"],
        responses={200: AddressListResponseSerializer()}
    )
    def get(self, request):
        addresses = Address.objects.filter(
            user=request.user
        ).order_by("-is_default", "-created_at")
        serializer = AddressSerializer(addresses, many=True)
        return Response({
            "detail": "Addresses retrieved successfully",
            "data": serializer.data,
            "success": True
        })
    
    @swagger_auto_schema(
        operation_id="create_address",
        operation_description="Create a new delivery address. If is_default is true, other addresses will be unmarked as default.",
        tags=["Commerce - Address"],
        request_body=AddressCreateSerializer,
        responses={
            201: AddressResponseSerializer(),
            400: BAD_REQUEST_400
        }
    )
    def post(self, request):
        serializer = AddressCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                if serializer.validated_data.get("is_default") is True:
                    Address.objects.filter(
                        user=request.user
                    ).update(is_default=False)

                address = serializer.save(user=request.user)

        except IntegrityError:
            return Response(
                {
                    "detail": "This address already exists.",
                    "data": None,
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "detail": "Address created successfully",
                "data": AddressSerializer(address).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="get_address",
        operation_description="Get details of a specific address.",
        tags=["Commerce - Address"],
        responses={
            200: AddressResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def get(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found", "data": None, "success": False}, status=404)

        serializer = AddressSerializer(address)
        return Response({
            "detail": "Address retrieved successfully",
            "data": serializer.data,
            "success": True
        })

    @swagger_auto_schema(
        operation_id="update_address",
        operation_description="Update an existing address. Setting is_default to true will unmark other addresses.",
        tags=["Commerce - Address"],
        request_body=AddressUpdateSerializer,
        responses={
            200: AddressResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def patch(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found", "data": None, "success": False}, status=404)

        serializer = AddressUpdateSerializer(
            address,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("is_default") is True:
            Address.objects.filter(
                user=request.user,
                is_default=True
            ).exclude(id=address.id).update(is_default=False)

        address = serializer.save()
        return Response({
            "detail": "Address updated successfully",
            "data": AddressSerializer(address).data,
            "success": True
        })

    @swagger_auto_schema(
        operation_id="delete_address",
        operation_description="Delete a delivery address.",
        tags=["Commerce - Address"],
        responses={
            200: StandardResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def delete(self, request, address_id):
        deleted_count, _ = Address.objects.filter(
            id=address_id,
            user=request.user
        ).delete()

        if deleted_count == 0:
            return Response(
                {"detail": "Address not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"detail": "Address deleted successfully", "data": None, "success": True},
            status=status.HTTP_200_OK
        )


# Get Wishlist
class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="get_wishlist",
        operation_description="Get the current user's wishlist with all saved products.",
        tags=["Commerce - Wishlist"],
        responses={200: WishlistResponseSerializer()}
    )
    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response({
            "detail": "Wishlist retrieved successfully",
            "data": serializer.data,
            "success": True
        })

# Add Item to Wishlist
class AddToWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="add_to_wishlist",
        operation_description="Add a product to the wishlist. Returns error if product already exists in wishlist.",
        tags=["Commerce - Wishlist"],
        request_body=AddToWishlistSerializer,
        responses={
            201: StandardResponseSerializer(),
            400: BAD_REQUEST_400
        }
    )
    def post(self, request):
        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        product_id = serializer.validated_data["product_id"]

        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product_id=product_id
        )

        if not created:
            return Response(
                {"detail": "Product already in wishlist", "data": None, "success": False},
                status=400
            )

        return Response(
            {"detail": "Added to wishlist", "data": None, "success": True},
            status=201
        )

# Remove item from Wishlist
class RemoveFromWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="remove_from_wishlist",
        operation_description="Remove a product from the wishlist.",
        tags=["Commerce - Wishlist"],
        responses={
            200: StandardResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def delete(self, request, item_id):
        deleted, _ = WishlistItem.objects.filter(
            id=item_id,
            wishlist__user=request.user
        ).delete()

        if not deleted:
            return Response({"detail": "Item not found", "data": None, "success": False}, status=404)

        return Response({"detail": "Removed from wishlist", "data": None, "success": True})

class OrderHistoryPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class OrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = OrderHistoryPagination

    @swagger_auto_schema(
        operation_id="list_orders",
        operation_description="Get the order history for the current user with pagination.",
        tags=["Commerce - Orders"],
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Items per page (max 50)", type=openapi.TYPE_INTEGER),
        ],
        responses={200: OrderHistorySerializer(many=True)}
    )
    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).order_by("-created_at")

        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)

        serializer = OrderHistorySerializer(paginated_orders, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "Orders retrieved successfully",
            "data": response_data,
            "success": True
        })

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="get_order_detail",
        operation_description="Get detailed information about a specific order including items and address.",
        tags=["Commerce - Orders"],
        responses={
            200: OrderDetailResponseSerializer(),
            404: NOT_FOUND_404
        }
    )
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found", "data": None, "success": False}, status=404)

        serializer = OrderHistorySerializer(order)
        return Response({
            "detail": "Order retrieved successfully",
            "data": serializer.data,
            "success": True
        })


#### ADMIN APIS FOR PRODUCTS ####
class AdminProductListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminProductListCreateAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = AdminProductListPagination

    @swagger_auto_schema(auto_schema=None)    
    def get(self, request):
        search_term = request.query_params.get("search", None)
        status = request.query_params.get("status", None)
        category = request.query_params.get("category", None)
        user_type = request.query_params.get("user_type", None)

        products = Product.objects.all().order_by("-created_at")
        if search_term:
            products = products.filter(
                Q(name__icontains=search_term) |
                Q(brand__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        if status:
            if status == "outofstock":
                products = products.filter(stock_quantity__lte=0)
            elif status == "instock":
                products = products.filter(stock_quantity__gt=0)
        
        if user_type == "patient":
            print(user_type)
            products = products.filter(for_patients=True)

        elif user_type == "doctor":
            print(user_type)
            products = products.filter(for_doctors=True)
        
        if category:
            products = products.filter(category=category)
        
        paginator = self.pagination_class()    
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = AdminProductReadSerializer(paginated_products, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True
        return Response(response_data)


    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = AdminProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            AdminProductReadSerializer(product).data,
            status=status.HTTP_201_CREATED
        )

class AdminProductUpdateAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = AdminProductWriteSerializer(
            product, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            AdminProductReadSerializer(product).data,
            status=status.HTTP_200_OK
        )

class AdminCouponPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminCouponListCreateView(APIView): 
    permission_classes = [IsAdmin]
    pagination_class = AdminCouponPagination

    @swagger_auto_schema(responses={200: CouponSerializer(many=True)}, auto_schema=None)
    def get(self, request):
        search_term = request.query_params.get("search", None)
        status = request.query_params.get("is_active", None)
        coupon_type = request.query_params.get("coupon_type", None)
        coupons = Coupon.objects.all().order_by("-created_at")
        
        if search_term:
            coupons = Coupon.objects.filter(
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        if status:
            coupons = coupons.filter(is_active=(status == "true"))
        if coupon_type:
            coupons = coupons.filter(discount_type=coupon_type)

        
        serializer = CouponSerializer(coupons, many=True)
        paginator = self.pagination_class()
        paginated_coupons = paginator.paginate_queryset(coupons, request)
        serializer = CouponSerializer(paginated_coupons, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True
        return Response(response_data)


    @swagger_auto_schema(
        request_body=CouponSerializer,
        responses={201: "Coupon created"},
        auto_schema=None
    )
    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save()
        return Response({"success": True, "data": CouponSerializer(coupon).data})

class AdminCouponUpdateDestroyView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        request_body=CouponSerializer,
        responses={200: "Coupon updated"},
        auto_schema=None
    )
    def patch(self, request, coupon_id):
        coupon = get_object_or_404(Coupon, id=coupon_id)
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save()
        return Response({"success": True, "data": CouponSerializer(coupon).data})
    
    @swagger_auto_schema(responses={200: "Coupon deleted"}, auto_schema=None)
    def delete(self, request, coupon_id):
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.delete()
        return Response({"success": True, "message": "Coupon deleted"})

class AdminCreateShopCategoryAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_id="create_shop_category",
        operation_description="Create a shop landing category with image (multipart/form-data)",
        tags=["Commerce - Shop"],
        request_body=AdminShopCategoryWriteSerializer
    )
    def post(self, request):
        serializer = AdminShopCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response({
            "success": True,
            "detail": "Shop category created successfully",
            "data": ShopCategorySerializer(
                category,
                context={"request": request}
            ).data
        }, status=201)

class AdminCreateShopBannerAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_id="create_shop_banner",
        operation_description="Create a shop landing banner with image (multipart/form-data)",
        tags=["Commerce - Shop"],
        request_body=AdminShopBannerWriteSerializer
    )
    def post(self, request):
        serializer = AdminShopBannerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        banner = serializer.save()

        return Response({
            "success": True,
            "detail": "Shop banner created successfully",
            "data": ShopBannerSerializer(
                banner,
                context={"request": request}
            ).data
        }, status=201)

#### ADMIN APIS FOR ORDERS ####

class AdminOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminOrderListAPIView(APIView):
    """Admin endpoint to list orders with filters and analytics."""
    permission_classes = [IsAdmin]
    pagination_class = AdminOrderPagination

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        # Get filter parameters
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        # Base queryset
        queryset = Order.objects.all().order_by("-created_at")

        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(id__icontains=search) |
                Q(user__full_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        # Paginate
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(queryset, request)

        serializer = AdminOrderListSerializer(paginated_orders, many=True, context={"request": request})
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data["success"] = True

        return Response(response_data)

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        """Create a new order manually."""
        from apps.accounts.models import User
        from decimal import Decimal
        
        serializer = AdminCreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get user and address
        user = User.objects.get(id=data["user_id"])
        address = Address.objects.get(id=data["address_id"])

        # Calculate total amount from items
        total_amount = Decimal("0.00")
        order_items_data = []
        
        for item in data["items"]:
            product = Product.objects.get(id=item["product_id"])
            # Calculate final price (with discount and tax)
            unit_price = product.get_unit_final_price()
            line_total = unit_price * item["quantity"]
            total_amount += line_total
            order_items_data.append({
                "product": product,
                "quantity": item["quantity"],
                "price_at_purchase": unit_price
            })

        # Create order
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                address=address,
                status=data.get("status", "pending_payment"),
                total_amount=total_amount,
                payment_method=data["payment_method"],
                payment_reference=data.get("payment_reference", "")
            )

            # Create order items
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item_data["product"],
                    quantity=item_data["quantity"],
                    price_at_purchase=item_data["price_at_purchase"]
                )
            
                # Reduce stock
                product.stock_quantity -= item_data["quantity"]

                # If stock hits zero → notify admin
                if product.stock_quantity <= 0:
                    product.stock_quantity = 0  # safety clamp

                    create_admin_notification(
                        title="Out of stock",
                        message=(
                            f"The product '{product.name}' is now out of stock "
                            f"after manual order #{order.id}. Please restock inventory."
                        ),
                        data={
                            "product_id": str(product.id),
                            "order_id": str(order.id),
                            "trigger": "manual_admin_order"
                        }
                    )
                    product.save(update_fields=["stock_quantity"])

        return Response(
            {
                "success": True,
                "message": "Order created successfully",
                "data": AdminOrderDetailSerializer(order, context={"request": request}).data
            },
            status=status.HTTP_201_CREATED
        )

class AdminUserAddressListView(APIView):
    """Admin endpoint to get addresses for a specific user."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, user_id):
        from apps.accounts.models import User
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"success": False, "detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        addresses = Address.objects.filter(user=user).order_by("-is_default", "-created_at")
        serializer = AddressSerializer(addresses, many=True)
        
        return Response({
            "success": True,
            "results": serializer.data
        })

class AdminOrderDetailAPIView(APIView):
    """Admin endpoint to get order details."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        serializer = AdminOrderDetailSerializer(order, context={"request": request})
        return Response({
            "success": True,
            "data": serializer.data
        })

class AdminOrderUpdateStatusAPIView(APIView):
    """Admin endpoint to update order status."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order.status = serializer.validated_data["status"]
        order.save(update_fields=["status", "updated_at"])

        return Response({
            "success": True,
            "message": "Order status updated successfully",
            "data": AdminOrderDetailSerializer(order, context={"request": request}).data
        })


#### PAYMENT APIs ####

class CreatePaymentOrderView(APIView):
    """Create an order and initiate Razorpay payment."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="create_payment_order",
        operation_description="Create a Razorpay payment order from the user's cart. Returns Razorpay order details for client-side payment initiation.",
        tags=["Commerce - Payment"],
        request_body=CreatePaymentOrderSerializer,
        responses={
            201: openapi.Response(
                description="Payment order created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'order_id': openapi.Schema(type=openapi.TYPE_STRING, description='Internal order ID'),
                                'razorpay_order_id': openapi.Schema(type=openapi.TYPE_STRING, description='Razorpay order ID'),
                                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description='Amount in paise'),
                                'currency': openapi.Schema(type=openapi.TYPE_STRING),
                                'key_id': openapi.Schema(type=openapi.TYPE_STRING, description='Razorpay key ID'),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Cart is empty or stock unavailable")
        }
    )
    def post(self, request):
        serializer = CreatePaymentOrderSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        address_id = serializer.validated_data["address_id"]

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response(
                {"success": False, "detail": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_items = cart.items.filter(saved_for_later=False)
        if not cart_items.exists():
            return Response(
                {"success": False, "detail": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pre-calc item totals (no DB locking yet)
        order_items_data = []
        subtotal = Decimal("0.00")

        for cart_item in cart_items:
            product = cart_item.product

            if product.stock_quantity < cart_item.quantity:
                return Response(
                    {"success": False, "detail": f"{product.name} is out of stock"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            unit_price = product.get_unit_final_price()
            item_total = unit_price * cart_item.quantity
            subtotal += item_total

            order_items_data.append({
                "product": product,
                "quantity": cart_item.quantity,
                "price_at_purchase": unit_price,
            })

        with transaction.atomic():
            # Lock cart row to prevent parallel checkout
            cart = Cart.objects.select_for_update().get(id=cart.id)

            total_amount = subtotal

            # Lock and validate coupon (FIXED)
            if cart.coupon:
                coupon = Coupon.objects.select_for_update().get(id=cart.coupon.id)

                if not coupon.is_valid(cart_total=total_amount):
                    return Response(
                        {"success": False, "detail": "Coupon no longer valid"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if coupon.discount_type == "percentage":
                    discount = total_amount * (coupon.discount_value / Decimal("100"))
                else:
                    discount = coupon.discount_value

                if coupon.max_discount_amount:
                    discount = min(discount, coupon.max_discount_amount)

                total_amount -= discount

            total_amount = round(total_amount, 2)

            address = Address.objects.get(id=address_id)

            order = Order.objects.create(
                user=user,
                address=address,
                status=OrderStatus.PENDING_PAYMENT,
                total_amount=total_amount,
                payment_method="razorpay",
                payment_reference="",
                coupon=cart.coupon,
            )

            for item in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    quantity=item["quantity"],
                    price_at_purchase=item["price_at_purchase"],
                )

            amount_in_paise = int(total_amount * 100)

            razorpay_order = razorpay_service.create_order(
                amount=amount_in_paise,
                currency="INR",
                receipt=str(order.id),
                notes={
                    "order_id": str(order.id),
                    "user_id": str(user.id),
                },
            )

            Payment.objects.create(
                order=order,
                razorpay_order_id=razorpay_order["id"],
                amount=total_amount,
                currency="INR",
                status=PaymentStatus.CREATED,
            )

            # Clear coupon after use
            cart.coupon = None
            cart.save(update_fields=["coupon"])

        return Response(
            {
                "success": True,
                "detail": "Payment order created",
                "data": {
                    "order_id": str(order.id),
                    "razorpay_order_id": razorpay_order["id"],
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "key_id": settings.RAZORPAY_KEY_ID,
                    "prefill": {
                        "name": user.full_name,
                        "email": user.email,
                    },
                },
            },
            status=status.HTTP_201_CREATED,
        )

class VerifyPaymentView(APIView):
    """Verify Razorpay payment signature and complete the order."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="verify_payment",
        operation_description="Verify the Razorpay payment signature after successful payment. Completes the order and clears the cart.",
        tags=["Commerce - Payment"],
        request_body=VerifyPaymentSerializer,
        responses={
            200: openapi.Response(
                description="Payment verified and order completed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'order_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'payment_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Payment verification failed"),
            404: openapi.Response(description="Payment not found")
        }
    )
    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        razorpay_order_id = serializer.validated_data["razorpay_order_id"]
        razorpay_payment_id = serializer.validated_data["razorpay_payment_id"]
        razorpay_signature = serializer.validated_data["razorpay_signature"]

        # Find the payment record
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
        except Payment.DoesNotExist:
            return Response(
                {"success": False, "detail": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify that this payment belongs to the current user
        if payment.order.user != request.user:
            return Response(
                {"success": False, "detail": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verify signature
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )

        if not is_valid:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "Signature verification failed"
            payment.save()
            return Response(
                {"success": False, "detail": "Payment verification failed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        payment_details = razorpay_service.fetch_payment(razorpay_payment_id)

        with transaction.atomic():
            # Update payment record
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = PaymentStatus.CAPTURED
            payment.save()

            # Update order status
            order = payment.order
            order.status = OrderStatus.PAID
            order.payment_reference = razorpay_payment_id
            order.payment_method = payment_details.get("method")
            order.payment_meta = payment_details  # 🔥 Full JSON stored
            order.save()

            for item in order.items.select_related("product"):
                product = item.product
                product.stock_quantity -= item.quantity
                if product.stock_quantity <= 0:
                    product.stock_quantity = 0  # safety clamp
                    create_admin_notification(
                        title="Out of stock",
                        message=(
                            f"The product '{product.name}' is now out of stock "
                            f"after order #{order.id}. Please restock inventory."
                        ),
                        data={
                            "product_id": str(product.id),
                            "order_id": str(order.id)
                        }
                    )
                product.save(update_fields=["stock_quantity"])

            # Clear the user's cart
            Cart.objects.filter(user=request.user).delete()

            # Increment coupon usage if used
            if order.coupon:
                order.coupon.current_uses += 1
                order.coupon.save(update_fields=["current_uses"])

        return Response({
            "detail": "Payment verified successfully",
            "data": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "status": order.status
            },
            "success": True
        })

class PaymentWebhookView(APIView):
    """Handle Razorpay webhook events."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id="payment_webhook",
        operation_description="Webhook endpoint for Razorpay to send payment event notifications. Do not call directly.",
        tags=["Commerce - Payment"],
        responses={
            200: openapi.Response(description="Webhook processed"),
            400: openapi.Response(description="Invalid payload")
        }
    )
    def post(self, request):
        # Get webhook payload
        payload = request.body.decode("utf-8")
        signature = request.headers.get("X-Razorpay-Signature", "")

        # Note: In production, you should verify the webhook signature
        # webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        # if not razorpay_service.verify_webhook_signature(payload, signature, webhook_secret):
        #     return Response({"detail": "Invalid signature"}, status=400)

        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON"},
                status=status.HTTP_400_BAD_REQUEST
            )

        event = event_data.get("event")
        payment_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})

        if not payment_entity:
            return Response({"detail": "No payment data"}, status=400)

        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        if not razorpay_order_id:
            return Response({"detail": "No order_id in payload"}, status=400)

        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=404)

        if event == "payment.captured":
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = PaymentStatus.CAPTURED
            payment.save()

            order = payment.order
            order.status = OrderStatus.PAID
            order.payment_reference = razorpay_payment_id
            order.save()

        elif event == "payment.failed":
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = payment_entity.get("error_description", "Payment failed")
            payment.save()

            order = payment.order
            order.status = OrderStatus.CANCELLED
            order.save()

        elif event == "refund.created":
            payment.status = PaymentStatus.REFUNDED
            payment.save()

            order = payment.order
            order.status = OrderStatus.REFUNDED
            order.save()

        return Response({"detail": "Webhook processed", "data": None, "success": True})

class RetryPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, order_id):

        # Fetch order
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        # Must be pending payment
        if order.status != OrderStatus.PENDING_PAYMENT:
            return Response(
                {"detail": "Payment retry not allowed for this order", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If a payment was already captured → block
        if order.payments.filter(status=PaymentStatus.CAPTURED).exists():
            return Response(
                {"detail": "Order already paid", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check stock availability again
        for item in order.items.select_related("product"):
            if item.product.stock_quantity < item.quantity:
                return Response(
                    {
                        "detail": f"{item.product.name} is out of stock",
                        "data": None,
                        "success": False
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Create new Razorpay order
        amount_in_paise = int(order.total_amount * 100)

        try:
            razorpay_order = razorpay_service.create_order(
                amount=amount_in_paise,
                currency="INR",
                receipt=str(order.id),
                notes={"order_id": str(order.id), "user_id": str(request.user.id)}
            )
        except Exception:
            return Response(
                {"detail": "Failed to initiate payment retry", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store new payment record
        Payment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order["id"],
            amount=order.total_amount,
            currency="INR",
            status=PaymentStatus.CREATED
        )

        return Response({
            "detail": "Payment retry initiated",
            "data": {
                "order_id": str(order.id),
                "razorpay_order_id": razorpay_order["id"],
                "amount": amount_in_paise,
                "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID,
                "prefill": {
                    "name": request.user.full_name,
                    "email": request.user.email
                }
            },
            "success": True
        }, status=status.HTTP_201_CREATED)

class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CancelOrderSerializer,
        responses={200: StandardResponseSerializer()},
        tags=["Commerce - Orders"],
        operation_id="cancel_order",
        operation_description="Cancel an order.",
    )
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        # Disallow invalid transitions
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, 
                            OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
            return Response(
                {"detail": "Order cannot be cancelled at this stage", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            previous_status = order.status
            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status", "updated_at"])

            # If stock was already reduced, restore it
            if previous_status in [OrderStatus.PAID, OrderStatus.PROCESSING]:
                for item in order.items.select_related("product"):
                    product = item.product
                    product.stock_quantity += item.quantity
                    product.save(update_fields=["stock_quantity"])

            # Optional: admin notification
            # create_admin_notification(
            #     title="Order Cancelled",
            #     message=f"Order #{order.id} was cancelled by user.",
            #     data={
            #         "order_id": str(order.id),
            #         "user_id": str(request.user.id),
            #         "reason": reason
            #     }
            # )

        return Response({
            "detail": "Order cancelled successfully",
            "data": {"order_id": str(order.id), "status": order.status},
            "success": True
        })

class RefundOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=RefundRequestSerializer,
        responses={200: StandardResponseSerializer()},
        tags=["Commerce - Orders"],
        operation_id="refund_order",
        operation_description="Refund an order.",
    )
    def post(self, request, order_id):
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        # Fetch order
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        # Disallow invalid states
        if order.status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
            return Response(
                {"detail": "Order already closed", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status not in [OrderStatus.PAID, OrderStatus.PROCESSING]:
            return Response(
                {"detail": "Order not eligible for refund", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check payment record
        try:
            payment = order.payments.get(status=PaymentStatus.CAPTURED)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "No successful payment found", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check refund eligibility per product
        non_refundable_products = []
        for item in order.items.select_related("product"):
            if not item.product.is_refundable:
                non_refundable_products.append(item.product.name)

        if non_refundable_products:
            return Response(
                {
                    "detail": "Some products in this order are non-refundable",
                    "data": {"non_refundable": non_refundable_products},
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # All good → proceed refund
        with transaction.atomic():
            try:
                # Razorpay refund (amount in paise)
                refund = razorpay_service.refund_payment(
                    payment.razorpay_payment_id,
                    amount=int(payment.amount * 100),
                    notes={
                        "order_id": str(order.id),
                        "reason": reason
                    }
                )
            except Exception as e:
                return Response(
                    {"detail": "Refund initiation failed", "data": None, "success": False},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update payment
            payment.status = PaymentStatus.REFUNDED
            payment.save(update_fields=["status", "updated_at"])

            # Update order
            order.status = OrderStatus.REFUNDED
            order.save(update_fields=["status", "updated_at"])

            # Restore stock
            for item in order.items.select_related("product"):
                product = item.product
                product.stock_quantity += item.quantity
                product.save(update_fields=["stock_quantity"])

            # Admin notification
            create_admin_notification(
                title="Order Refunded",
                message=f"Order #{order.id} was refunded successfully.",
                data={
                    "order_id": str(order.id),
                    "user_id": str(request.user.id),
                    "refund_id": refund.get("id")
                }
            )

        return Response({
            "detail": "Refund completed successfully",
            "data": {
                "order_id": str(order.id),
                "status": order.status
            },
            "success": True
        })


