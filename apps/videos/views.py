from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q, F
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404

from apps.videos.models import Video, VideoBookmark
from apps.videos.constants import Status
from apps.videos.serializers import (
    VideoListSerializer, VideoDetailSerializer, VideoCreateSerializer, VideoUpdateSerializer, 
    VideoReviewSerializer, AdminVideoCreateSerializer, PaginatedVideosListResponseSerializer,
    VideoBookmarkSerializer
)
from core.permissions import IsDoctor, IsAdmin

class VideoPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class VideoListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = VideoPagination

    @swagger_auto_schema(responses={200: PaginatedVideosListResponseSerializer()})
    def get(self, request):

        queryset = Video.objects.filter(
            status=Status.PUBLISHED,
            is_deleted=False
        )

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if sort == "oldest":
            queryset = queryset.order_by("created_at")
        elif sort == "mostViewed":
            queryset = queryset.order_by("-view_count")
        elif sort == "mostDownloaded":
            queryset = queryset.order_by("-download_count")
        else:
            queryset = queryset.order_by("-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = VideoListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Videos fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class VideoDetailView(APIView):
    """
    Retrieve a published video and increment its view count.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: VideoDetailSerializer()})
    def get(self, request, id):

        # Step 1: Fetch only published + non-deleted videos
        video = get_object_or_404(
            Video,
            id=id,
            status=Status.PUBLISHED,
            is_deleted=False
        )

        # Step 2: Atomic increment of view count
        Video.objects.filter(id=video.id).update(
            view_count=F("view_count") + 1
        )

        # Step 3: Refresh updated value
        video.refresh_from_db()

        # Step 4: Serialize response
        serializer = VideoDetailSerializer(
            video,
            context={"request": request}
        )

        return Response({
            "detail": "Video retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class VideoDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: VideoDetailSerializer()})
    def post(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            status=Status.PUBLISHED,
            is_deleted=False
        )

        if not video.allow_download:
            return Response({
                "detail": "Downloads are disabled for this video.",
                "success": False
            }, status=400)

        Video.objects.filter(id=video.id).update(
            download_count=F("download_count") + 1
        )

        video.refresh_from_db()

        return Response({
            "detail": "Download count updated",
            "download_count": video.download_count,
            "success": True
        })

class MyVideoListView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = VideoPagination

    @swagger_auto_schema(responses={200: PaginatedVideosListResponseSerializer()})
    def get(self, request):

        queryset = Video.objects.filter(
            uploaded_by=request.user,
            is_deleted=False
        ).order_by("-created_at")

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = VideoListSerializer(
            page, many=True,
            context={"request": request}
        )

        return Response({
            "detail": "My videos fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True
        })

class MyVideoDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(responses={200: VideoDetailSerializer()})
    def get(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            uploaded_by=request.user,
            is_deleted=False
        )

        serializer = VideoDetailSerializer(
            video,
            context={"request": request}
        )

        return Response({
            "detail": "My video retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class MyVideoDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(responses={200: VideoDetailSerializer()})
    def post(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            uploaded_by=request.user,
            is_deleted=False
        )

        # Ensure file exists
        if not video.video_file:
            raise Http404("Video file not found.")

        file_path = video.video_file.path

        try:
            response = FileResponse(
                open(file_path, "rb"),
                as_attachment=True,
                filename=video.video_file.name.split("/")[-1]
            )
            return response

        except FileNotFoundError:
            raise Http404("Video file not found.")
        
class VideoCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        request_body=VideoCreateSerializer(),
        responses={201: VideoDetailSerializer()}
    )
    def post(self, request):

        serializer = VideoCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        serializer.save(
            uploaded_by=request.user,
            status=Status.DRAFT
        )

        return Response({
            "detail": "Video uploaded as draft",
            "success": True
        }, status=status.HTTP_201_CREATED)

class VideoUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        request_body=VideoUpdateSerializer(),
        responses={200: VideoDetailSerializer()}
    )
    def patch(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            uploaded_by=request.user,
            is_deleted=False
        )

        if video.status != Status.DRAFT:
            return Response({
                "detail": "Only draft videos can be edited.",
                "success": False
            }, status=400)

        serializer = VideoUpdateSerializer(
            video,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Video updated successfully",
            "success": True
        })

class MyBookmarkedVideosView(APIView):
    """
    List all videos bookmarked by the authenticated user.
    Only returns published and non-deleted videos.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = VideoPagination

    @swagger_auto_schema(responses={200: PaginatedVideosListResponseSerializer()})
    def get(self, request):

        # Step 1: Filter bookmarked videos
        queryset = Video.objects.filter(
            bookmarks__user=request.user,
            status=Status.PUBLISHED,
            is_deleted=False
        ).order_by("-created_at")

        # Step 2: Optional filters (consistent with VideoListView)
        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        sort = request.GET.get("sort", "newest")

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if sort == "oldest":
            queryset = queryset.order_by("created_at")
        elif sort == "mostViewed":
            queryset = queryset.order_by("-view_count")
        elif sort == "mostDownloaded":
            queryset = queryset.order_by("-download_count")
        else:
            queryset = queryset.order_by("-created_at")

        # Step 3: Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = VideoListSerializer(
            page,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Bookmarked videos fetched successfully",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class ToggleVideoBookmarkView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: VideoBookmarkSerializer()})
    def post(self, request, id):
        # Step 1: Ensure video exists and is published
        video = get_object_or_404(
            Video,
            id=id,
            status=Status.PUBLISHED,
            is_deleted=False
        )

        # Step 2: Check if bookmark exists
        bookmark = VideoBookmark.objects.filter(
            user=request.user,
            video=video
        ).first()

        # Step 3: Toggle logic
        if bookmark:
            bookmark.delete()
            return Response({
                "detail": "Video removed from bookmarks",
                "is_bookmarked": False,
                "success": True
            })

        # Create bookmark
        VideoBookmark.objects.create(
            user=request.user,
            video=video
        )

        return Response({
            "detail": "Video bookmarked successfully",
            "is_bookmarked": True,
            "success": True
        })

class SoftDeleteVideoView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(responses={200: VideoDetailSerializer()})
    def delete(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            uploaded_by=request.user,
            is_deleted=False
        )

        video.is_deleted = True
        video.save(update_fields=["is_deleted"])

        return Response({
            "detail": "Video deleted successfully",
            "success": True
        })



class AdminVideoCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):

        serializer = AdminVideoCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Video created and published successfully",
            "success": True
        }, status=status.HTTP_201_CREATED)

class AdminVideoUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            is_deleted=False
        )

        serializer = VideoUpdateSerializer(
            video,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Video updated successfully",
            "success": True
        })

class AdminVideoListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):

        queryset = Video.objects.all().order_by("-created_at")

        status_filter = request.GET.get("status")
        speciality = request.GET.get("speciality")
        search = request.GET.get("search")
        is_deleted = request.GET.get("is_deleted")

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        if is_deleted is not None:
            queryset = queryset.filter(
                is_deleted=is_deleted.lower() == "true"
            )

        serializer = VideoListSerializer(
            queryset,
            many=True,
            context={"request": request}
        )

        return Response({
            "detail": "Admin videos fetched successfully",
            "data": serializer.data,
            "success": True
        })

class AdminMoveToReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            status=Status.DRAFT,
            is_deleted=False
        )

        video.status = Status.REVIEW
        video.save(update_fields=["status"])

        return Response({
            "detail": "Video moved to review successfully",
            "success": True
        })

class VideoReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, id):

        video = get_object_or_404(
            Video,
            id=id,
            status=Status.REVIEW,
            is_deleted=False
        )

        serializer = VideoReviewSerializer(
            video,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Video review updated successfully",
            "success": True
        })
