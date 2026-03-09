from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from drf_yasg.utils import swagger_auto_schema
from apps.books.models import Book, BookPurchase
from apps.books.constants import Status, OrderStatus
from core.permissions import IsAdmin


class BooksAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_books = Book.objects.count()
        pending_books = Book.objects.filter(status=Status.PENDING).count()
        in_review_books = Book.objects.filter(status=Status.INREVIEW).count()
        approved_books = Book.objects.filter(status=Status.APPROVED).count()
        rejected_books = Book.objects.filter(status=Status.REJECTED).count()
        data = {
            "total_books": total_books,
            "pending_books": pending_books,
            "in_review_books": in_review_books,
            "approved_books": approved_books,
            "rejected_books": rejected_books,
        }
        return Response(data)

class BookPurchasesAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_purchases = BookPurchase.objects.count()
        total_revenue = BookPurchase.objects.filter(order_status=OrderStatus.PAID).aggregate(
            total_revenue=models.Sum("book__price"))["total_revenue"] or 0
        active_buyers = BookPurchase.objects.filter(order_status=OrderStatus.PAID).values("user").distinct().count()
        refunded_purchases = BookPurchase.objects.filter(order_status=OrderStatus.REFUNDED).count()
        avg_order_value = BookPurchase.objects.filter(order_status=OrderStatus.PAID).aggregate(
            avg_order_value=models.Avg("book__price"))["avg_order_value"] or 0
        data = {
            "totalPurchases": total_purchases,
            "totalRevenue": total_revenue,
            "activeBuyers": active_buyers,
            "refundRequests": refunded_purchases,
            "avgOrderValue": avg_order_value,
        }
        return Response(data)