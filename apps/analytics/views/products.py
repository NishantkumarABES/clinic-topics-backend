from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.commerce.models import Product
from core.permissions import IsAdmin


class ProductAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_products = Product.objects.count()
        for_patients_only = Product.objects.filter(for_patients=True).count()
        for_doctors_only = Product.objects.filter(for_doctors=True).count()
        for_both = Product.objects.filter(for_patients=True, for_doctors=True).count()

        out_of_stock_products = Product.objects.filter(stock_quantity__lte=0).count()
        in_stock_products = total_products - out_of_stock_products


        data = {
            "total_products": total_products,
            "instock_products": in_stock_products,
            "outofstock_products": out_of_stock_products,
            "distributions": {
                "for_patients_only": for_patients_only,
                "for_doctors_only": for_doctors_only,
                "for_both": for_both
            },
            "success": True
        }
        return Response(data)
