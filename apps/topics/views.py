from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.timezone import now
from django.core.files.storage import default_storage
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.topics.services import inshort_generator, check_transcription_status, start_transcription
from apps.topics.models import Topic
from apps.topics.serializers import (
    TopicListSerializer, TopicDetailSerializer, ArticleExtractionSerializer, CleanupImagesSerializer, AdminTopicReadSerializer,
    AdminTopicWriteSerializer, DoctorTopicCreateSerializer, TopicCreateSuccessResponseSerializer
)
from apps.notifications.services import create_admin_notification
from core.permissions import IsAdmin, IsDoctor


class TopicListView(generics.ListAPIView):
    serializer_class = TopicListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Topic.objects.filter(publish_status=True).order_by("-publishing_time")
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
    pagination_class = AdminTopicListPagination

    @swagger_auto_schema(
        auto_schema=None,
        operation_summary="List topics",
        responses={200: AdminTopicReadSerializer(many=True)}
    )
    def get(self, request):
        search_term = request.query_params.get("search")
        publish_status = request.query_params.get("status")
        

        queryset = Topic.objects.all()

        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        if publish_status:
            queryset = queryset.filter(publish_status=(publish_status=='publish'))


        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            queryset.order_by("-created_at"), request
        )

        serializer = AdminTopicReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    @swagger_auto_schema(
        auto_schema=None,
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
                "detail": "Topic created successfully",
                "data": AdminTopicReadSerializer(topic).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class AdminTopicUpdateAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
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
                "detail": "Topic updated successfully",
                "data": AdminTopicReadSerializer(topic).data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

class AdminTopicUpdatePublishStatusAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None, responses={200: "Success"})
    def patch(self, request, topic_id):
        topic = get_object_or_404(Topic, id=topic_id)
        topic.publish_status = not topic.publish_status
        topic.save()

        return Response(
            {"detail": "Publish status updated successfully", "data": None, "success": True}
        )

class ExtractArticleDataView(generics.CreateAPIView):
    serializer_class = ArticleExtractionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    swagger_schema = None
    
    @swagger_auto_schema(
        auto_schema=None,
        request_body=ArticleExtractionSerializer,
        responses={200: "Success"}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]

        try:
            summary, title, image_paths = inshort_generator(url)
            return Response(
                {
                    "detail": "Article data extracted successfully",
                    "data": {
                        "title": title,
                        "summary": summary,
                        "images": image_paths,
                    },
                    "success": True
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            return Response(
                {
                    "detail": str(exc),
                    "data": None,
                    "success": False
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
   
class CleanupUnwantedImages(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
        request_body=CleanupImagesSerializer,
        responses={200: "Success"}
    )
    def post(self, request):
        serializer = CleanupImagesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_urls = serializer.validated_data["image_urls"]

        deleted = []
        failed = []

        for url in image_urls:
            path = url.split("/v1/")[-1]
            default_storage.delete(path)
            deleted.append(path)

        return Response(
            {
                "detail": "Cleanup completed",
                "data": {
                    "deleted_count": len(deleted),
                    "failed_count": len(failed),
                    "deleted": deleted,
                    "failed": failed,
                },
                "success": True
            },
            status=status.HTTP_200_OK,
        )

class DoctorTopicCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Create / Upload new educational topic (Doctors only)",
        tags=['Doctor - Topics'],
        request_body=DoctorTopicCreateSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="Topic successfully created and queued for approval",
                schema=TopicCreateSuccessResponseSerializer,
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "title": ["This field is required."],
                        "video_url": ["Enter a valid URL."]
                    }
                }
            ),
            status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided.",
            status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
        }
    )
    def post(self, request):
        serializer = DoctorTopicCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        doctor_full_name = request.user.full_name
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        create_admin_notification(
            title="Topic Upload Request",
            message="Dr. {doctor_full_name} has submitted a new topic for approval.",
        ) 
        return Response(
            {
                "success": True,
                "message": "Topic uploaded successfully and sent for admin approval.",
                "data": AdminTopicReadSerializer(topic).data
            },
            status=status.HTTP_201_CREATED
        )

class TopicsFeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class TopicsFeedView(APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = TopicsFeedPagination

    @swagger_auto_schema(
        operation_summary="Get topics feed with advertisements",
        operation_description=(
            "Returns a paginated list of topics with advertisements inserted "
            "after every N topics. The interval is admin-configurable.\n\n"
            "Each item in the feed has a 'type' field that is either 'topic' or 'advertisement'."
        ),
        tags=['Advt - Topics'],
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description='Page number',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description='Number of items per page (max 50)',
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Feed items retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "next": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "previous": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "ad_interval": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "type": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        enum=["topic", "advertisement"]
                                    ),
                                }
                            )
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        from apps.cms.models import SiteConfiguration
        from apps.advertisements.models import Advertisement
        from apps.topics.serializers import TopicFeedItemSerializer, AdvertisementFeedItemSerializer
        from apps.accounts.constants import UserRole
        import random

        # Get ad interval from site configuration
        try:
            config = SiteConfiguration.get_config()
            ad_interval = config.ad_interval
        except Exception:
            ad_interval = 5  # Default fallback

        # Get published topics ordered by publishing time
        topics_queryset = Topic.objects.filter(publish_status=True).order_by("-publishing_time")

        # Get enabled advertisements, filtered by specialization for doctors
        ads_queryset = Advertisement.objects.filter(status='enabled')

        user = request.user
        if user.is_authenticated and user.role == UserRole.DOCTOR:
            # For doctors, filter by matching specialization
            try:
                doctor_profile = user.doctor_profile
                doctor_specialty = doctor_profile.specialization

                if doctor_specialty:
                    # Filter advertisements where specializations contains the doctor's specialty
                    ads_queryset = ads_queryset.filter(specializations__contains=[doctor_specialty])
            except AttributeError:
                # Doctor profile doesn't exist, show no ads
                ads_queryset = Advertisement.objects.none()

        enabled_ads = list(ads_queryset)

        # Paginate topics
        paginator = self.pagination_class()
        paginated_topics = paginator.paginate_queryset(topics_queryset, request)

        # Build feed with ads inserted
        feed_items = []
        topic_counter = 0

        for topic in paginated_topics:
            # Add topic to feed
            topic_data = TopicFeedItemSerializer(topic).data
            feed_items.append(topic_data)
            topic_counter += 1

            # Insert ad after every ad_interval topics
            if topic_counter % ad_interval == 0 and enabled_ads:
                # Pick a random advertisement
                ad = random.choice(enabled_ads)
                ad_data = {
                    "type": "advertisement",
                    "id": str(ad.id),
                    "title": ad.title,
                    "url": ad.url,
                    "image": request.build_absolute_uri(ad.image.url) if ad.image else None,
                }
                feed_items.append(ad_data)

        # Build response
        response_data = paginator.get_paginated_response(feed_items).data
        response_data['ad_interval'] = ad_interval

        return Response({
            "detail": "Topics feed retrieved successfully",
            "data": response_data,
            "success": True
        })


#########  TRANSCRIPTION APIs ######################

class StartTranscriptionAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
        operation_summary="Start transcription for a topic's video",
        responses={
            200: openapi.Response(
                description="Transcription started successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Transcription started successfully",
                        "data": {
                            "transcription_id": "uuid",
                            "sonix_media_id": "string",
                            "status": "preparing"
                        }
                    }
                }
            ),
            400: "Bad request - topic has no video URL or transcription already exists"
        }
    )
    def post(self, request, topic_id):
        try:
            result = start_transcription(topic_id)
            return Response(
                {
                    "detail": "Transcription started successfully",
                    "data": result,
                    "success": True
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TranscriptionStatusAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
        operation_summary="Get transcription status for a topic",
        responses={200: "Transcription status"}
    )
    def get(self, request, topic_id):
        try:
            result = check_transcription_status(topic_id)
            return Response(
                {
                    "detail": "Transcription status retrieved successfully",
                    "data": result,
                    "success": True
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DownloadTranscriptAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
        operation_summary="Download transcript text for a topic",
        responses={200: "Transcript text content"}
    )
    def get(self, request, topic_id):
        from apps.topics.models import Topic
        from django.http import HttpResponse
        
        try:
            topic = get_object_or_404(Topic, id=topic_id)
            
            if not hasattr(topic, 'transcription'):
                return Response(
                    {"detail": "No transcription exists for this topic", "data": None, "success": False},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            transcription = topic.transcription
            
            if not transcription.transcript_text:
                return Response(
                    {"detail": "Transcript text not available yet", "data": None, "success": False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return as downloadable text file
            response = HttpResponse(transcription.transcript_text, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="transcript_{topic_id}.txt"'
            return response
            
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DownloadTranscriptSRTAPIView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        auto_schema=None,
        operation_summary="Download transcript SRT file for a topic",
        responses={200: "Transcript SRT content"}
    )
    def get(self, request, topic_id):
        from apps.topics.models import Topic
        from django.http import HttpResponse
        
        try:
            topic = get_object_or_404(Topic, id=topic_id)
            
            if not hasattr(topic, 'transcription'):
                return Response(
                    {"detail": "No transcription exists for this topic", "data": None, "success": False},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            transcription = topic.transcription
            
            if not transcription.transcript_srt:
                return Response(
                    {"detail": "Transcript SRT not available yet", "data": None, "success": False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Return as downloadable SRT file
            response = HttpResponse(transcription.transcript_srt, content_type='text/srt')
            response['Content-Disposition'] = f'attachment; filename="transcript_{topic_id}.srt"'
            return response
            
        except Exception as e:
            return Response(
                {"detail": str(e), "data": None, "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
