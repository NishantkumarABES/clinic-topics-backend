from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Count, Value
from django.db.models.functions import Coalesce, TruncDate

from drf_yasg.utils import swagger_auto_schema
from dateutil.relativedelta import relativedelta

from apps.commerce.models import Product, OrderItem, OrderStatus, Order
from apps.accounts.models import User
from apps.topics.models import Topic
from apps.advertisements.models import Advertisement, AdvertisementStatus
from apps.books.models import Book
from apps.books.constants import Status as BookStatus
from apps.articles.models import Article
from apps.articles.constants import Status as ArticleStatus
from apps.videos.models import Video
from apps.videos.constants import Status as VideoStatus
from apps.jobs.models import JobPost
from apps.jobs.constants import JobPostStatus
from core.permissions import IsAdmin


class AdminDashboardMetricsAPIView(APIView):
    permission_classes = [IsAdmin]

    def calculate_growth_percentage(self, current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        current_time = now()

        # Month boundaries
        start_current_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_previous_month = start_current_month - relativedelta(months=1)
        start_two_months_ago = start_current_month - relativedelta(months=2)

        # Doctors
        current_doctors = User.objects.filter(
            role="doctor",
            created_at__gte=start_current_month
        ).count()

        previous_doctors = User.objects.filter(
            role="doctor",
            created_at__gte=start_previous_month,
            created_at__lt=start_current_month
        ).count()

        total_doctors = User.objects.filter(role="doctor").count()

        # Patients
        current_patients = User.objects.filter(
            role="patient",
            created_at__gte=start_current_month
        ).count()

        previous_patients = User.objects.filter(
            role="patient",
            created_at__gte=start_previous_month,
            created_at__lt=start_current_month
        ).count()

        total_patients = User.objects.filter(role="patient").count()

        # Topics
        current_topics = Topic.objects.filter(
            created_at__gte=start_current_month
        ).count()

        previous_topics = Topic.objects.filter(
            created_at__gte=start_previous_month,
            created_at__lt=start_current_month
        ).count()

        total_topics = Topic.objects.count()

        # Products
        current_products = Product.objects.filter(
            created_at__gte=start_current_month
        ).count()

        previous_products = Product.objects.filter(
            created_at__gte=start_previous_month,
            created_at__lt=start_current_month
        ).count()

        total_products = Product.objects.count()

        data = {
            "doctors": {
                "total": total_doctors,
                "growth_percent": self.calculate_growth_percentage(
                    current_doctors, previous_doctors
                ),
            },
            "patients": {
                "total": total_patients,
                "growth_percent": self.calculate_growth_percentage(
                    current_patients, previous_patients
                ),
            },
            "topics": {
                "total": total_topics,
                "growth_percent": self.calculate_growth_percentage(
                    current_topics, previous_topics
                ),
            },
            "products": {
                "total": total_products,
                "growth_percent": self.calculate_growth_percentage(
                    current_products, previous_products
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
        total_pending_books = Book.objects.filter(status=BookStatus.PENDING).count()
        total_inreview_books = Book.objects.filter(status=BookStatus.INREVIEW).count()
        total_draft_articles = Article.objects.filter(status=ArticleStatus.DRAFT).count()
        total_inreview_articles = Article.objects.filter(status=ArticleStatus.REVIEW).count()
        total_pending_videos = Video.objects.filter(status=VideoStatus.PENDING).count()
        total_inreview_videos = Video.objects.filter(status=VideoStatus.REVIEW).count()
        total_draft_jobs = JobPost.objects.filter(status=JobPostStatus.DRAFT).count()
        total_inreview_jobs = JobPost.objects.filter(status=JobPostStatus.IN_REVIEW).count()

        data = {
            "out_of_stock_products": total_out_of_stock_products,
            "unpublished_topics": total_unpublished_topics,
            "unpublished_advt": total_unpublished_advt,
            "pending_books": total_pending_books,
            "in_review_books": total_inreview_books,
            "draft_articles": total_draft_articles,
            "in_review_articles": total_inreview_articles,
            "pending_videos": total_pending_videos,
            "in_review_videos": total_inreview_videos,
            "draft_jobs": total_draft_jobs,
            "in_review_jobs": total_inreview_jobs,
        }
        return Response(data)

class TopSellingProductsAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
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

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        qs = Order.objects.filter(status=OrderStatus.PAID)

        # ✅ Apply filters dynamically
        if year:
            qs = qs.filter(created_at__year=year)

        if month:
            qs = qs.filter(created_at__month=month)

        # ✅ Aggregation
        qs = (
            qs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                revenue=Sum("total_amount"),
                orders=Count("id")
            )
            .order_by("date")
        )

        # ✅ Response formatting
        response = [
            {
                "date": row["date"].strftime("%b %d").replace(" 0", " "),
                "revenue": float(row["revenue"] or 0),
                "orders": int(row["orders"] or 0),
            }
            for row in qs
        ]

        return Response(response)

class OrderStatusAnalyticsAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
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