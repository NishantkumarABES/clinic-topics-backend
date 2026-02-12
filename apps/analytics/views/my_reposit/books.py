from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.books.models import Book
from apps.books.constants import Status
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
