from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now, localtime
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count, Value
from django.db.models.functions import Coalesce, TruncWeek

from drf_yasg.utils import swagger_auto_schema
from datetime import timedelta

from apps.commerce.models import Product, OrderItem, OrderStatus, Order
from apps.accounts.models import User
from apps.topics.models import Topic
from apps.advertisements.models import Advertisement, AdvertisementStatus
from core.permissions import IsAdmin


class AdminDashboardMetricsAPIView(APIView):
    permission_classes = [IsAdmin]

    def calculate_growth_percentage(self, new_count, previous_total):
        if previous_total <= 0:
            return 100 if new_count > 0 else 0
        return round((new_count / previous_total) * 100, 2)

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        now_time = now()
        last_month = now_time - timedelta(days=30)

        # Doctors
        total_doctors = User.objects.filter(role="doctor").count()
        new_doctors = User.objects.filter(
            role="doctor",
            created_at__gte=last_month
        ).count()
        previous_doctors = total_doctors - new_doctors

        # Patients
        total_patients = User.objects.filter(role="patient").count()
        new_patients = User.objects.filter(
            role="patient",
            created_at__gte=last_month
        ).count()
        previous_patients = total_patients - new_patients

        # Topics
        total_topics = Topic.objects.count()
        new_topics = Topic.objects.filter(
            created_at__gte=last_month
        ).count()
        previous_topics = total_topics - new_topics

        # Products
        total_products = Product.objects.count()
        new_products = Product.objects.filter(
            created_at__gte=last_month
        ).count()
        previous_products = total_products - new_products
        data = {
            "doctors": {
                "total": total_doctors,
                "growth_percent": self.calculate_growth_percentage(
                    new_doctors, previous_doctors
                ),
            },
            "patients": {
                "total": total_patients,
                "growth_percent": self.calculate_growth_percentage(
                    new_patients, previous_patients
                ),
            },
            "topics": {
                "total": total_topics,
                "growth_percent": self.calculate_growth_percentage(
                    new_topics, previous_topics
                ),
            },
            "products": {
                "total": total_products,
                "growth_percent": self.calculate_growth_percentage(
                    new_products, previous_products
                ),
            }
        }

        return Response(data)

class AdminDashboardPendingActionAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_out_of_stock_products = Product.objects.filter(stock_quantity=0).count()
        total_unpublished_topics = Topic.objects.filter(publish_status=False).count()
        total_unpublished_advt = Advertisement.objects.filter(status=AdvertisementStatus.DISABLED).count()
        data = {
            "out_of_stock_products": total_out_of_stock_products,
            "unpublished_topics": total_unpublished_topics,
            "unpublished_advt": total_unpublished_advt
        }
        return Response(data)

class TopSellingProductsAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        completed_items = OrderItem.objects.filter(
            order__status=OrderStatus.PAID   # or COMPLETED
        )

        # revenue = quantity * price_at_purchase
        revenue_expression = ExpressionWrapper(
            F("quantity") * F("price_at_purchase"),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )

        qs = (
            completed_items
            .values("product_id", "product__name")
            .annotate(
                quantity_sold=Coalesce(Sum("quantity"), Value(0)),
                revenue=Coalesce(
                    Sum(revenue_expression),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
                )
            )
            .order_by("-revenue")[:10]
        )

        response = [
            {
                "id": row["product_id"],
                "name": row["product__name"],
                "quantity_sold": int(row["quantity_sold"]),
                "revenue": float(row["revenue"])
            }
            for row in qs
        ]

        return Response(response)

class RevenueAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]

    # @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        qs = (
            Order.objects
            .filter(status=OrderStatus.PAID)
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(
                revenue=Sum("total_amount"),
                orders=Count("id")
            )
            .order_by("week")
        )

        response = []
        for row in qs:
            week_date = localtime(row["week"]).date()
            date_str = week_date.strftime("%b %d").replace(" 0", " ")
            response.append({
                "date": date_str,  # e.g. Jan 1
                "revenue": float(row["revenue"]),
                "orders": int(row["orders"])
            })

        return Response(response)

class OrderStatusAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]

    # @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        # Aggregate counts per status
        qs = (
            Order.objects
            .values("status")
            .annotate(count=Count("id"))
        )

        total_orders = sum(row["count"] for row in qs) or 1  # avoid division by zero

        response = [
            {
                "status": row["status"],
                "count": row["count"],
                "percentage": round((row["count"] / total_orders) * 100, 2)
            }
            for row in qs
        ]

        # Optional: enforce consistent ordering based on your frontend status list
        status_order = [
            OrderStatus.PENDING_PAYMENT,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED
        ]

        response.sort(key=lambda x: status_order.index(x["status"]) if x["status"] in status_order else 999)

        return Response(response)