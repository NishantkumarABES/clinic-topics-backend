from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Sum

from apps.commerce.models import Order
from apps.commerce.constants import OrderStatus
from core.permissions import IsAdmin



class OrdersAnalyticsView(APIView):
    """Admin endpoint to get order analytics."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
    # Get all orders (no date filter)
        all_orders = Order.objects.all()

        # Calculate analytics
        total_orders = all_orders.count()
        paid_orders = all_orders.filter(status=OrderStatus.PAID).count()
        pending_payments = all_orders.filter(status=OrderStatus.PENDING_PAYMENT).count()
        processing_orders = all_orders.filter(status=OrderStatus.PROCESSING).count()
        delivered_orders = all_orders.filter(status=OrderStatus.DELIVERED).count()
        cancelled_orders = all_orders.filter(status=OrderStatus.CANCELLED).count()
        refunded_orders = all_orders.filter(status=OrderStatus.REFUNDED).count()


        # Total revenue (from successful/active orders)
        total_revenue = all_orders.filter(
            status__in=["paid", "processing", "shipped", "delivered"]
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        refund_amount = all_orders.filter(
            status=OrderStatus.REFUNDED
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        net_revenue = total_revenue - refund_amount


        return Response({
            "success": True,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "pending_payments": pending_payments,
            "processing_orders": processing_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "refunded_orders": refunded_orders,
            "total_revenue": float(total_revenue),
            "refund_amount": float(refund_amount),
            "net_revenue": float(net_revenue),
        })