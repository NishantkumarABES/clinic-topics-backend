from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import F, Q

from apps.articles.models import Article, Bookmark
from apps.articles.serializers import (
    ArticleListSerializer, ArticleDetailSerializer, ArticleListResponseSerializer
)
from core.api_responses import NOT_FOUND_404, SUCCESS_200
from core.permissions import IsDoctor, IsAdmin
from drf_yasg.utils import swagger_auto_schema

class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class ArticleListView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]
    pagination_class = ArticlePagination

    @swagger_auto_schema(
        responses={
            200: ArticleListResponseSerializer(),
        }
    )
    def get(self, request):
        queryset = Article.objects.filter(status="published")
        # -------- filters --------
        search = request.GET.get("search")
        specialty = request.GET.get("specialty")
        article_type = request.GET.get("type")
        year = request.GET.get("year")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(abstract__icontains=search)
            )

        if specialty:
            queryset = queryset.filter(specialty=specialty)

        if article_type:
            queryset = queryset.filter(article_type=article_type)

        if year:
            queryset = queryset.filter(year=year)

        # -------- sorting --------

        if sort == "oldest":
            queryset = queryset.order_by("upload_date")

        elif sort == "alphabetical":
            queryset = queryset.order_by("title")

        elif sort == "mostViewed":
            queryset = queryset.order_by("-view_count")

        else:
            queryset = queryset.order_by("-upload_date")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ArticleListSerializer(
            page, many=True, context={"user": request.user}
        )
        response = paginator.get_paginated_response(serializer.data).data
        return Response(
            {
                "details": "Articles retrieved successfully",
                "data": response,
                "success": True
            }
        )

class ArticleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]

    @swagger_auto_schema(
        responses={
            200: ArticleDetailSerializer(),
            404: NOT_FOUND_404,
        }
    )
    def get(self, request, slug):
        try:
            article = Article.objects.get(
                slug=slug, status="published"
            )
        except Article.DoesNotExist:
            return Response(
                {
                    "details": "Article not found",
                    "data": None,
                    "success": False
                }
            )


        # atomic increment
        Article.objects.filter(
            id=article.id
        ).update(view_count=F("view_count") + 1)

        article.refresh_from_db()

        serializer = ArticleDetailSerializer(
            article,
            context={"user": request.user}
        )

        return Response(
            {
                "details": "Article retrieved successfully",
                "data": serializer.data,
                "success": True
            }
        )

class ToggleBookmarkView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]

    @swagger_auto_schema(
        responses={
            200: ArticleDetailSerializer(),
            404: NOT_FOUND_404,
        }
    )
    def post(self, request, slug):

        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response(
                {
                    "details": "Article not found",
                    "data": None,
                    "success": False
                }
            )

        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            article=article
        )

        if not created:
            bookmark.delete()
            return Response(
                {
                    "details": "Bookmark removed",
                    "data": {"bookmarked": False},
                    "success": True
                }
            )

        return Response(
            {
                "details": "Bookmark added",
                "data": {"bookmarked": True},
                "success": True
            }
        )

class ArticleDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]

    @swagger_auto_schema(
        responses={
            200: SUCCESS_200,
            404: NOT_FOUND_404,
        }
    )
    def post(self, request, slug):

        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response(
                {
                    "details": "Article not found",
                    "data": None,
                    "success": False
                }
            )

        Article.objects.filter(
            id=article.id
        ).update(download_count=F("download_count") + 1)

        return Response(
            {
                "details": "Download count incremented",
                "data": None,
                "success": True
            }
        )