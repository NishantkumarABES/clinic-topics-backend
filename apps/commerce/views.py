from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from core.permissions import IsAdmin
from apps.commerce.models import Product, Cart, CartItem, Address, Coupon, ProductReview, Wishlist, WishlistItem, Order
from apps.commerce.serializers import (
    ProductListSerializer, ProductDetailSerializer, CartSerializer, AddToCartSerializer, AddressSerializer,
    AddressCreateSerializer, AddressUpdateSerializer, AdminProductReadSerializer, AdminProductWriteSerializer,
    ProductReviewSerializer, CreateUpdateReviewSerializer, ApplyCouponSerializer, CouponSerializer,
    WishlistSerializer, AddToWishlistSerializer, WishlistItem, OrderHistorySerializer,
    AdminOrderListSerializer, AdminOrderDetailSerializer, UpdateOrderStatusSerializer
)
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta


class ProductListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = ProductListPagination
    
    @swagger_auto_schema(responses={200: ProductListSerializer(many=True)})
    def get(self, request):
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        min_price = request.query_params.get("min_price", 0)
        max_price = request.query_params.get("max_price", 999999999)
        brand = request.query_params.get("brand")
        queryset = Product.objects.filter(is_out_of_stock=False)

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
        response_data['success'] = True
        return Response(response_data)

class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: ProductDetailSerializer()})
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found"},
                status=404
            )

        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)

class ProductReviewListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: ProductReviewSerializer(many=True)})
    def get(self, request, product_id):
        reviews = ProductReview.objects.filter(product_id=product_id).order_by("-created_at")
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })

class CreateUpdateProductReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CreateUpdateReviewSerializer,
        responses={200: ProductReviewSerializer}
    )
    def post(self, request):
        serializer = CreateUpdateReviewSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response({
            "success": True,
            "data": ProductReviewSerializer(review).data
        })

class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ApplyCouponSerializer,
        responses={200: "Coupon applied"}
    )
    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        coupon = Coupon.objects.get(code__iexact=code)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Calculate cart total
        total = 0
        for item in cart.items.filter(saved_for_later=False):
            total += item.get_final_price() * item.quantity

        total = round(total, 2)

        # Use model validation
        if not coupon.is_valid(cart_total=total):
            return Response(
                {"success": False, "detail": "Coupon is not valid for this cart"},
                status=400
            )

        # Attach coupon to cart
        cart.coupon = coupon
        cart.save(update_fields=["coupon"])

        return Response({
            "success": True,
            "message": "Coupon applied successfully"
        })

class RemoveCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.coupon = None
        cart.save(update_fields=["coupon"])
        return Response({
            "success": True,
            "message": "Coupon removed"
        })


class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: CartSerializer()})
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    @swagger_auto_schema(request_body=AddToCartSerializer(), responses={201: "Item added to cart"})
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

        return Response({"message": "Item added to cart", "success" : True}, status=201)

class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=AddToCartSerializer(), responses={200: "Cart updated"})
    def patch(self, request, item_id):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
        except CartItem.DoesNotExist:
            return Response({"detail": "Item not found"}, status=404)

        quantity = request.data.get("quantity")
        saved_for_later = request.data.get("saved_for_later")

        if quantity is not None:
            if quantity <= 0:
                item.delete()
                return Response({"message": "Item removed"})
            item.quantity = quantity

        if saved_for_later is not None:
            item.saved_for_later = saved_for_later

        item.save()
        return Response({"message": "Cart updated", "success" : True})

class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: "Item removed"})
    def delete(self, request, item_id):
        CartItem.objects.filter(
            id=item_id, cart__user=request.user
        ).delete()
        return Response({"message": "Item removed", "success" : True})

class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: AddressSerializer(many=True)})
    def get(self, request):
        addresses = Address.objects.filter(
            user=request.user
        ).order_by("-is_default", "-created_at")
        serializer = AddressSerializer(addresses, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })
    
    @swagger_auto_schema(
        request_body=AddressCreateSerializer,
        responses={
            201: AddressSerializer,
            400: "Duplicate address"
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
                    "success": False,
                    "detail": "This address already exists."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "success": True,
                "data": AddressSerializer(address).data
            },
            status=status.HTTP_201_CREATED
        )

class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: AddressSerializer()})
    def get(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found"}, status=404)

        serializer = AddressSerializer(address)
        serializer.data["success"] = True
        return Response({
            "success": True,
            "data": serializer.data
        })

    @swagger_auto_schema(
        request_body=AddressUpdateSerializer,
        responses={200: AddressSerializer}
    )
    def patch(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found"}, status=404)

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
            "success": True,
            "data": AddressSerializer(address).data
        })

    @swagger_auto_schema(
        responses={200: "Address deleted", 404: "Address not found"}
    )
    def delete(self, request, address_id):
        deleted_count, _ = Address.objects.filter(
            id=address_id,
            user=request.user
        ).delete()

        if deleted_count == 0:
            return Response(
                {"detail": "Address not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"success": True},
            status=status.HTTP_200_OK
        )


# Get Wishlist
class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: WishlistSerializer()})
    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response({"success": True, "data": serializer.data})

# Add Item to Wishlist
class AddToWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=AddToWishlistSerializer,
        responses={201: "Added to wishlist"}
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
                {"success": False, "detail": "Product already in wishlist"},
                status=400
            )

        return Response(
            {"success": True, "message": "Added to wishlist"},
            status=201
        )

# Remove item from Wishlist
class RemoveFromWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: "Removed from wishlist"})
    def delete(self, request, item_id):
        deleted, _ = WishlistItem.objects.filter(
            id=item_id,
            wishlist__user=request.user
        ).delete()

        if not deleted:
            return Response({"detail": "Item not found"}, status=404)

        return Response({"success": True, "message": "Removed from wishlist"})

class OrderHistoryPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 50

class OrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = OrderHistoryPagination

    @swagger_auto_schema(responses={200: OrderHistorySerializer(many=True)})
    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).order_by("-created_at")

        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)

        serializer = OrderHistorySerializer(paginated_orders, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data["success"] = True
        return Response(response_data)

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: OrderHistorySerializer()})
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        serializer = OrderHistorySerializer(order)
        return Response({"success": True, "data": serializer.data})


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


        products = Product.objects.all().order_by("-created_at")
        if search_term:
            products = products.filter(
                Q(name__icontains=search_term) |
                Q(brand__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        if status:
            products = products.filter(is_out_of_stock=(status=='outofstock'))
        
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

    @swagger_auto_schema(responses={200: CouponSerializer(many=True)})
    def get(self, request):
        search_term = request.query_params.get("search", None)
        status = request.query_params.get("status", None)
        coupon_type = request.query_params.get("coupon_type", None)

        if search_term:
            coupons = Coupon.objects.filter(
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        if status:
            coupons = coupons.filter(is_active=(status=='active'))
        if coupon_type:
            coupons = coupons.filter(coupon_type=coupon_type)

        coupons = Coupon.objects.all().order_by("-created_at")
        serializer = CouponSerializer(coupons, many=True)
        paginator = self.pagination_class()
        paginated_coupons = paginator.paginate_queryset(coupons, request)
        serializer = CouponSerializer(paginated_coupons, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True
        return Response(response_data)


    @swagger_auto_schema(
        request_body=CouponSerializer,
        responses={201: "Coupon created"}
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
        responses={200: "Coupon updated"}
    )
    def patch(self, request, coupon_id):
        coupon = get_object_or_404(Coupon, id=coupon_id)
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save()
        return Response({"success": True, "data": CouponSerializer(coupon).data})
    
    @swagger_auto_schema(responses={200: "Coupon deleted"})
    def delete(self, request, coupon_id):
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.delete()
        return Response({"success": True, "message": "Coupon deleted"})


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


class AdminOrderAnalyticsAPIView(APIView):
    """Admin endpoint to get order analytics."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        # Get today's orders
        today_orders = Order.objects.filter(created_at__gte=today_start)

        # Calculate analytics
        total_orders_today = today_orders.count()
        pending_payments = Order.objects.filter(status="pending_payment").count()
        processing_orders = Order.objects.filter(status="processing").count()
        delivered_orders = Order.objects.filter(status="delivered").count()
        cancelled_orders = Order.objects.filter(status="cancelled").count()

        # Today's revenue (from delivered orders)
        total_revenue_today = today_orders.filter(
            status__in=["paid", "processing", "shipped", "delivered"]
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        return Response({
            "success": True,
            "total_orders_today": total_orders_today,
            "pending_payments": pending_payments,
            "processing_orders": processing_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue_today": float(total_revenue_today),
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