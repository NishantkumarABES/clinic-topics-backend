from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db.models import Q

from core.permissions import IsAdmin
from apps.commerce.models import Category, Product, Cart, CartItem, Address, Prescription
from apps.commerce.serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer, CartSerializer, AddToCartSerializer, AddressSerializer,
    PrescriptionUploadSerializer, AttachPrescriptionSerializer, AdminProductReadSerializer, AdminProductWriteSerializer
)


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(responses={200: CategorySerializer(many=True)}, auto_schema=None)
    def get(self, request):
        categories = Category.objects.filter(is_active=True, parent__isnull=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

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
        queryset = Product.objects.filter(is_out_of_stock=False)


        if category:
            queryset = queryset.filter(category=category)

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

    @swagger_auto_schema(auto_schema=None, responses={200: ProductDetailSerializer()})
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found"},
                status=404
            )

        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)

class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, responses={200: CartSerializer()})
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, request_body=AddToCartSerializer(), responses={201: "Item added to cart"})
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

        return Response({"message": "Item added to cart"}, status=201)

class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, request_body=AddToCartSerializer(), responses={200: "Cart updated"})
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
        return Response({"message": "Cart updated"})

class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, responses={200: "Item removed"})
    def delete(self, request, item_id):
        CartItem.objects.filter(
            id=item_id, cart__user=request.user
        ).delete()
        return Response({"message": "Item removed"})

class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: AddressSerializer(many=True)}, auto_schema=None)
    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(auto_schema=None, request_body=AddressSerializer(), responses={201: AddressSerializer()})
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("is_default", False):
            Address.objects.filter(user=request.user).update(is_default=False)

        serializer.save(user=request.user)
        return Response(serializer.data, status=201)

class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, responses={200: AddressSerializer()})
    def patch(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found"}, status=404)

        serializer = AddressSerializer(
            address, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("is_default", False):
            Address.objects.filter(user=request.user).update(is_default=False)

        serializer.save()
        return Response(serializer.data)


    @swagger_auto_schema(auto_schema=None, responses={200: AddressSerializer()})
    def delete(self, request, address_id):
        Address.objects.filter(
            id=address_id, user=request.user
        ).delete()
        return Response(status=204)

class PrescriptionUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(auto_schema=None, request_body=PrescriptionUploadSerializer(), responses={201: "Prescription uploaded"})
    def post(self, request):
        serializer = PrescriptionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prescription = serializer.save(user=request.user)

        return Response(
            {
                "id": prescription.id,
                "message": "Prescription uploaded"
            },
            status=201
        )

class PrescriptionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, responses={200: PrescriptionUploadSerializer(many=True)})
    def get(self, request):
        prescriptions = Prescription.objects.filter(user=request.user)
        serializer = PrescriptionUploadSerializer(prescriptions, many=True)
        return Response(serializer.data)

class AttachPrescriptionToCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, request_body=AttachPrescriptionSerializer(), responses={200: "Prescription attached"})
    def post(self, request):
        serializer = AttachPrescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = CartItem.objects.get(
                id=serializer.validated_data["cart_item_id"],
                cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return Response({"detail": "Cart item not found"}, status=404)

        if not item.product.is_prescription_required:
            return Response(
                {"detail": "Prescription not required for this product"},
                status=400
            )

        try:
            prescription = Prescription.objects.get(
                id=serializer.validated_data["prescription_id"],
                user=request.user
            )
        except Prescription.DoesNotExist:
            return Response({"detail": "Prescription not found"}, status=404)

        item.prescription = prescription
        item.save(update_fields=["prescription"])

        return Response({"message": "Prescription attached"})

class OrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None, responses={200: "Order history not implemented yet"})
    def get(self, request):
        return Response({"message": "Order history not implemented yet"})
    




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
