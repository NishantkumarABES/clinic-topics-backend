from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404

from apps.articles.models import Article, Bookmark
from apps.articles.serializers import (
    ArticleListSerializer, ArticleDetailSerializer, ArticleCreateSerializer, ArticleUpdateSerializer, ArticleReviewSerializer,
    PaginatedArticlesListResponseSerializer
)
from apps.articles.constants import Status
from core.permissions import IsDoctor, IsAdmin



class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = ArticlePagination

    @swagger_auto_schema(
        responses={200: PaginatedArticlesListResponseSerializer()},
        operation_description="Retrieve a paginated list of published articles. Supports search, filtering and sorting.",
        manual_parameters=[
            openapi.Parameter(
                name="search",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Search in title or abstract (partial match)"
            ),
            openapi.Parameter(
                name="speciality",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by speciality"
            ),
            openapi.Parameter(
                name="type",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by article type"
            ),
            openapi.Parameter(
                name="year",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description="Filter by publication year"
            ),
            openapi.Parameter(
                name="sort",
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description='Ordering field(s), e.g. "-created_at", "title", etc. Default: "-created_at"',
                default="-created_at"
            ),
        ]
    )
    def get(self, request):

        queryset = Article.objects.filter(
            status=Status.PUBLISHED,
            is_deleted=False
        )

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        article_type = request.GET.get("type")
        year = request.GET.get("year")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(abstract__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if article_type:
            queryset = queryset.filter(article_type=article_type)

        if year:
            queryset = queryset.filter(year=year)

        if sort == "oldest":
            queryset = queryset.order_by("publication_date")
        elif sort == "alphabetical":
            queryset = queryset.order_by("title")
        elif sort == "mostViewed":
            queryset = queryset.order_by("-view_count")
        else:
            queryset = queryset.order_by("-publication_date")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ArticleListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Articles fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class ArticleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: ArticleDetailSerializer(),
        }
    )
    def get(self, request, id):

        article = get_object_or_404(
            Article, id=id,
            status=Status.PUBLISHED,
            is_deleted=False
        )

        Article.objects.filter(id=article.id).update(
            view_count=F("view_count") + 1
        )
        article.refresh_from_db()

        serializer = ArticleDetailSerializer(
            article,
            context={"request": request}
        )

        return Response({
            "detail": "Article retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class ArticleCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]

    @swagger_auto_schema(
        request_body=ArticleCreateSerializer(),
        responses={ 201: ArticleDetailSerializer()}
    )
    def post(self, request):

        serializer = ArticleCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        serializer.save(
            uploaded_by=request.user,
            status=Status.DRAFT
        )

        return Response({
            "detail": "Article saved as draft",
            "success": True
        }, status=status.HTTP_201_CREATED)

class MyArticlesView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = ArticlePagination

    @swagger_auto_schema(
        responses={
            200: PaginatedArticlesListResponseSerializer(),
        }
    )
    def get(self, request):

        queryset = Article.objects.filter(
            uploaded_by=request.user,
            is_deleted=False
        ).order_by("-created_at")

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        article_type = request.GET.get("type")
        year = request.GET.get("year")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(abstract__icontains=search)
            )
        
        if speciality:
            queryset = queryset.filter(speciality=speciality)
        
        if article_type:
            queryset = queryset.filter(article_type=article_type)
        
        if year:
            queryset = queryset.filter(year=year)
        
        if sort == "oldest":
            queryset = queryset.order_by("publication_date")
        
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ArticleListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "My articles fetched",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class ToggleBookmarkView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        {
            200: ArticleDetailSerializer(),
        }
    )
    def post(self, request, id):

        article = get_object_or_404(
            Article, id=id,
            status=Status.PUBLISHED,
            is_deleted=False
        )

        with transaction.atomic():

            bookmark = Bookmark.objects.filter(
                user=request.user,
                article=article
            ).first()

            if bookmark:
                bookmark.delete()

                return Response({
                    "detail": "Bookmark removed",
                    "data": {"bookmarked": False},
                    "success": True
                })

            Bookmark.objects.create(
                user=request.user,
                article=article
            )

        return Response({
            "detail": "Bookmark added",
            "data": {"bookmarked": True},
            "success": True
        }, status=status.HTTP_201_CREATED)

class BookmarkListView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = ArticlePagination

    @swagger_auto_schema(
        responses={200: PaginatedArticlesListResponseSerializer()}
    )
    def get(self, request):

        queryset = Article.objects.filter(
            bookmarks__user=request.user,
            is_deleted=False,
            status=Status.PUBLISHED
        ).select_related("uploaded_by").distinct()

        # ---- Filters ----
        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        article_type = request.GET.get("type")
        year = request.GET.get("year")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(abstract__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if article_type:
            queryset = queryset.filter(article_type=article_type)

        if year:
            queryset = queryset.filter(year=year)

        # ---- Sorting ----
        if sort == "oldest":
            queryset = queryset.order_by("publication_date")
        elif sort == "alphabetical":
            queryset = queryset.order_by("title")
        elif sort == "mostViewed":
            queryset = queryset.order_by("-view_count")
        else:
            queryset = queryset.order_by("-publication_date")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ArticleListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Bookmarked articles fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class ArticleUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={200: ArticleDetailSerializer()},
        request_body=ArticleUpdateSerializer()
    )
    def patch(self, request, id):

        article = get_object_or_404(
            Article, id=id,
            uploaded_by=request.user
        )

        if article.status != Status.DRAFT:
            return Response({
                "detail": "Only draft articles can be edited.",
                "success": False
            }, status=400)

        serializer = ArticleUpdateSerializer(
            article,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Article updated successfully",
            "success": True
        })

class SoftDeleteArticleView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_description="Soft delete an article uploaded by the authenticated user."
    )
    def delete(self, request, id):

        article = get_object_or_404(
            Article,
            id=id,
            uploaded_by=request.user,
            is_deleted=False
        )

        article.is_deleted = True
        article.save(update_fields=["is_deleted"])

        return Response({
            "detail": "Article deleted successfully.",
            "success": True
        }, status=status.HTTP_200_OK)





class AdminArticleListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = ArticlePagination

    @swagger_auto_schema(
        responses={200: PaginatedArticlesListResponseSerializer()}
    )
    def get(self, request):

        queryset = Article.objects.all().order_by("-created_at")

        # ---- Filters ----
        status_filter = request.GET.get("status")
        search = request.GET.get("search")
        article_type = request.GET.get("type")
        speciality = request.GET.get("speciality")
        year = request.GET.get("year")
        is_deleted = request.GET.get("is_deleted")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if is_deleted is not None:
            queryset = queryset.filter(is_deleted=is_deleted.lower() == "true")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(abstract__icontains=search)
            )

        if article_type:
            queryset = queryset.filter(article_type=article_type)

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if year:
            queryset = queryset.filter(year=year)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ArticleListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Admin articles fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class ArticleReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={200: ArticleDetailSerializer()},
        request_body=ArticleReviewSerializer()
    )
    def patch(self, request, id):

        article = get_object_or_404(
            Article, id=id,
            status=Status.REVIEW
        )

        serializer = ArticleReviewSerializer(
            article,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Article review updated",
            "success": True
        })

class AdminMoveToReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={200: ArticleDetailSerializer()},
        operation_description="Admin moves draft article to review state."
    )
    def patch(self, request, id):

        article = get_object_or_404(
            Article,
            id=id,
            status=Status.DRAFT
        )

        article.status = Status.REVIEW
        article.save(update_fields=["status"])

        return Response({
            "detail": "Article moved to review by admin",
            "success": True
        })
