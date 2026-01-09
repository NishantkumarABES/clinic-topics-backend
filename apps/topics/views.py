from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema


from apps.topics.services import inshort_generator
from apps.topics.models import Topic
from apps.topics.serializers import (
    TopicListSerializer, TopicDetailSerializer, ArticleExtractionSerializer,
    CleanupImagesSerializer, AdminTopicReadSerializer, AdminTopicWriteSerializer
)
from core.permissions import IsAdmin 
from external.cloudinary.utils import CloudinaryService
cloudinary = CloudinaryService()



class TopicListView(generics.ListAPIView):
    serializer_class = TopicListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Topic.objects.filter(publishing_time__lte=now())

        category_id = self.request.query_params.get("category")
        audience = self.request.query_params.get("audience")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if audience:
            queryset = queryset.filter(topic_audience=audience)

        return queryset

class TopicDetailView(generics.RetrieveAPIView):
    queryset = Topic.objects.filter(publishing_time__lte=now())
    serializer_class = TopicDetailSerializer
    permission_classes = [permissions.AllowAny]




#########  ADMIN TOPICS APIs ######################

class AdminTopicListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminTopicListCreateAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = AdminTopicListPagination

    @swagger_auto_schema(
        operation_summary="List topics",
        responses={200: AdminTopicReadSerializer(many=True)}
    )
    def get(self, request):
        search_term = request.query_params.get("search")

        queryset = Topic.objects.all()

        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            queryset.order_by("-created_at"), request
        )

        serializer = AdminTopicReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    @swagger_auto_schema(
        request_body=AdminTopicWriteSerializer,
        responses={201: AdminTopicReadSerializer}
    )
    def post(self, request):
        serializer = AdminTopicWriteSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()

        return Response(
            {
                "success": True,
                "data": AdminTopicReadSerializer(topic).data
            },
            status=status.HTTP_201_CREATED
        )

class AdminTopicUpdateAPIView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=AdminTopicWriteSerializer,
        responses={200: AdminTopicReadSerializer}
    )
    def patch(self, request, topic_id):
        topic = get_object_or_404(Topic, id=topic_id)

        serializer = AdminTopicWriteSerializer(
            topic,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()

        return Response(
            {
                "success": True,
                "data": AdminTopicReadSerializer(topic).data
            },
            status=status.HTTP_200_OK
        )

class AdminTopicUpdatePublishStatusAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema()
    def patch(self, request, topic_id):
        topic = get_object_or_404(Topic, id=topic_id)
        topic.publish_status = not topic.publish_status
        topic.save()

        return Response(
            {"success": True, "message": "Publish status updated successfully."}
        )

class ExtractArticleDataView(generics.CreateAPIView):
    serializer_class = ArticleExtractionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]

        try:
            summary, title, image_paths = inshort_generator(url)
            return Response(
                {
                    "success": True,
                    "title": title,
                    "summary": summary,
                    "images": image_paths,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            return Response(
                {
                    "success": False,
                    "error": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
   
class CleanupUnwantedImages(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        serializer = CleanupImagesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_urls = serializer.validated_data["image_urls"]

        deleted = []
        failed = []

        for url in image_urls:
            try:
                result = CloudinaryService.destroy_image(url=url)
                if result.get("result") == "ok": deleted.append(url)
                else: failed.append({"url": url, "reason": result.get("result")})
            except Exception as exc:
                failed.append(
                    {"url": url, "reason": str(exc)}
                )
        return Response(
            {
                "success": True,
                "deleted_count": len(deleted),
                "failed_count": len(failed),
                "deleted": deleted,
                "failed": failed,
            },
            status=status.HTTP_200_OK,
        )

