from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.articles.models import Article
from apps.articles.constants import Status
from core.permissions import IsAdmin


class ArticlesAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_articles = Article.objects.count()
        draft_articles = Article.objects.filter(status=Status.DRAFT).count()
        published_articles = Article.objects.filter(status=Status.PUBLISHED).count()
        rejected_articles = Article.objects.filter(status=Status.REJECTED).count()
        in_review_articles = Article.objects.filter(status=Status.INREVIEW).count()
        data = {
            "total_articles": total_articles,
            "draft_articles": draft_articles,
            "published_articles": published_articles,
            "rejected_articles": rejected_articles,
            "in_review_articles": in_review_articles,
        }
        return Response(data)
