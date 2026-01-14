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
from apps.commerce.models import Product, Cart, CartItem, Address, Coupon, ProductReview, Wishlist, WishlistItem, Order, OrderItem, Payment
from apps.commerce.models import PaymentStatus
from apps.commerce.serializers import (
    ProductListSerializer, ProductDetailSerializer, CartSerializer, AddToCartSerializer, AddressSerializer,
    AddressCreateSerializer, AddressUpdateSerializer, AdminProductReadSerializer, AdminProductWriteSerializer,
    ProductReviewSerializer, CreateUpdateReviewSerializer, ApplyCouponSerializer, CouponSerializer,
    WishlistSerializer, AddToWishlistSerializer, WishlistItem, OrderHistorySerializer,
    AdminOrderListSerializer, AdminOrderDetailSerializer, UpdateOrderStatusSerializer, AdminCreateOrderSerializer,
    CreatePaymentOrderSerializer, VerifyPaymentSerializer, PaymentSerializer
)
from apps.commerce.services import razorpay_service
from apps.commerce.constants import OrderStatus
from django.conf import settings
from decimal import Decimal
import json
from django.utils import timezone
from django.db.models import Sum


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
        queryset = Product.objects.filter(stock_quantity__gt=0)

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
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response({"success": False, "detail": "Invalid coupon"}, status=400)

        # Get cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Calculate cart total
        total = Decimal("0.00")
        for item in cart.items.filter(saved_for_later=False):
            total += item.get_total_price()

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

    @swagger_auto_schema(responses={200: CouponSerializer(many=True)}, auto_schema=None)
    def get(self, request):
        search_term = request.query_params.get("search", None)
        status = request.query_params.get("status", None)
        coupon_type = request.query_params.get("coupon_type", None)
        coupons = Coupon.objects.all().order_by("-created_at")
        
        if search_term:
            coupons = Coupon.objects.filter(
                Q(code__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        if status:
            coupons = coupons.filter(is_active=(status=='active'))
        if coupon_type:
            coupons = coupons.filter(coupon_type=coupon_type)

        
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


#### PAYMENT APIs ####

class CreatePaymentOrderView(APIView):
    """Create an order and initiate Razorpay payment."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CreatePaymentOrderSerializer,
        responses={201: "Payment order created"}
    )
    def post(self, request):
        serializer = CreatePaymentOrderSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        address_id = serializer.validated_data["address_id"]

        # Get user's cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response(
                {"success": False, "detail": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get cart items (not saved for later)
        cart_items = cart.items.filter(saved_for_later=False)
        if not cart_items.exists():
            return Response(
                {"success": False, "detail": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total amount
        total_amount = Decimal("0.00")
        order_items_data = []

        for cart_item in cart_items:
            product = cart_item.product

            # Check stock availability
            if product.stock_quantity < cart_item.quantity:
                return Response(
                    {"success": False, "detail": f"{product.name} is out of stock"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate final price with discount and tax
            unit_price = product.get_unit_final_price()
            item_total = unit_price * cart_item.quantity
            total_amount += item_total
            order_items_data.append({
                "product": product,
                "quantity": cart_item.quantity,
                "price_at_purchase": unit_price
            })

        # Apply coupon discount if any
        applied_coupon = None
        if cart.coupon and cart.coupon.is_valid(cart_total=total_amount):
            coupon = cart.coupon
            if coupon.discount_type == "percentage":
                discount = total_amount * (coupon.discount_value / Decimal("100"))
            else:
                discount = coupon.discount_value

            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)

            total_amount = total_amount - discount

        total_amount = round(total_amount, 2)

        with transaction.atomic():
            # Get address
            address = Address.objects.get(id=address_id)

            # Create Order
            order = Order.objects.create(
                user=user,
                address=address,
                status=OrderStatus.PENDING_PAYMENT,
                total_amount=total_amount,
                payment_method="razorpay",
                payment_reference=""
                coupon=cart.coupon
            )

            # Create OrderItems
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item_data["product"],
                    quantity=item_data["quantity"],
                    price_at_purchase=item_data["price_at_purchase"]
                )

            # Create Razorpay Order
            # Razorpay expects amount in paise (smallest currency unit)
            amount_in_paise = int(total_amount * 100)

            try:
                razorpay_order = razorpay_service.create_order(
                    amount=amount_in_paise,
                    currency="INR",
                    receipt=str(order.id),
                    notes={"order_id": str(order.id), "user_id": str(user.id)}
                )
            except Exception as e:
                # Rollback will happen automatically due to transaction.atomic()
                raise e

            # Create Payment record
            payment = Payment.objects.create(
                order=order,
                razorpay_order_id=razorpay_order["id"],
                amount=total_amount,
                currency="INR",
                status=PaymentStatus.CREATED
            )
            cart.coupon = None
            cart.save(update_fields=["coupon"])

        return Response({
            "success": True,
            "message": "Payment order created",
            "data": {
                "order_id": str(order.id),
                "razorpay_order_id": razorpay_order["id"],
                "amount": amount_in_paise,
                "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID,
                "prefill": {
                    "name": user.full_name,
                    "email": user.email,
                }
            }
        }, status=status.HTTP_201_CREATED)

class VerifyPaymentView(APIView):
    """Verify Razorpay payment signature and complete the order."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=VerifyPaymentSerializer,
        responses={200: "Payment verified"}
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
            order.save()

            for item in order.items.select_related("product"):
                product = item.product
                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity"])

            # Clear the user's cart
            Cart.objects.filter(user=request.user).delete()

            # Increment coupon usage if used
            if order.coupon:
                order.coupon.current_uses += 1
                order.coupon.save(update_fields=["current_uses"])

        return Response({
            "success": True,
            "message": "Payment verified successfully",
            "data": {
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "status": order.status
            }
        })

class PaymentWebhookView(APIView):
    """Handle Razorpay webhook events."""
    permission_classes = [AllowAny]

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

        return Response({"success": True, "message": "Webhook processed"})