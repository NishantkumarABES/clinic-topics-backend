import os, uuid, tempfile
from rest_framework import serializers
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.videos.models import Video, VideoBookmark
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.videos.constants import Status
from apps.videos.services import generate_thumbnail_moviepy


class VideoListSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    uploaded_by = serializers.StringRelatedField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id",
            "uploaded_by",
            "title",
            "Institution",
            "description",
            "speciality",
            "duration_seconds",
            "view_count",
            "video_file",
            "thumbnail",
            "download_count",
            "allow_download",
            "status",
            "created_at",
            "updated_at",
            "is_bookmarked",
            "is_deleted",
        ]

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return VideoBookmark.objects.filter(
            user=request.user,
            video=obj
        ).exists()

    def __init__(self, *args, **kwargs):
        """
        Hide moderation fields for non-admin users.
        """
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if not request:
            return

        if request.user.role != UserRole.ADMIN:
            self.fields.pop("is_deleted", None)
    
    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        if obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None
        
    
    def get_video_file(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        if obj.video_file:
            return request.build_absolute_uri(obj.video_file.url)
        return None
        
class VideoDetailSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Video
        fields = "__all__"

    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return VideoBookmark.objects.filter(
            user=request.user,
            video=obj
        ).exists()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and request.user.role != UserRole.ADMIN:
            self.fields.pop("is_deleted", None)

class VideoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        exclude = (
            "uploaded_by",
            "status",
            "view_count",
            "download_count",
            "rejection_reason",
            "duration_seconds",
            "thumbnail",
            "is_deleted",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        # Step 1: Create video object (S3 upload happens here)
        print("Creating video...")
        video = Video.objects.create(**validated_data)
        print("Video FIle", video.video_file)
        if video.video_file:
            self._process_video(video)

        return video

    def _process_video(self, video):
        # ---- 1. Extract original extension ----
        original_name = video.video_file.name
        _, ext = os.path.splitext(original_name)

        if not ext:
            ext = ".mp4"  # fallback (rare edge case)
        # ---- 2. Download video from storage ----
        with default_storage.open(original_name, "rb") as f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_video:
                for chunk in f.chunks():
                    temp_video.write(chunk)
                temp_video_path = temp_video.name
    
        # ---- 3. Generate thumbnail ----
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_thumb:
            temp_thumbnail_path = temp_thumb.name

        duration = generate_thumbnail_moviepy(
            temp_video_path,
            temp_thumbnail_path,
            time_in_seconds=1.0
        )
        # ---- 4. Save thumbnail back to S3 ----
        with open(temp_thumbnail_path, "rb") as thumb_file:
            thumbnail_name = f"videos/thumbnails/{uuid.uuid4()}.jpg"

            saved_path = default_storage.save(
                thumbnail_name,
                ContentFile(thumb_file.read())
            )

        # ---- 5. Update model ----
        video.thumbnail = saved_path
        if duration:
            video.duration_seconds = int(duration)

        video.save(update_fields=["thumbnail", "duration_seconds"])
        # ---- 6. Cleanup ----
        os.remove(temp_video_path)
        os.remove(temp_thumbnail_path)

class VideoUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Video
        exclude = (
            "uploaded_by",
            "status",
            "view_count",
            "download_count",
            "rejection_reason",
            "is_deleted",
            "created_at",
            "updated_at",
        )

class VideoReviewSerializer(serializers.ModelSerializer):

    REVIEW_STATUS = (
        (Status.PUBLISHED, "Publish"),
        (Status.REJECTED, "Reject"),
    )

    status = serializers.ChoiceField(choices=REVIEW_STATUS)
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Video
        fields = ("status", "rejection_reason")

    def validate(self, attrs):
        status_value = attrs.get("status")
        reason = attrs.get("rejection_reason")

        if status_value == Status.REJECTED and not reason:
            raise serializers.ValidationError(
                "Rejection reason is required when rejecting."
            )

        if status_value == Status.PUBLISHED:
            attrs["rejection_reason"] = None

        return attrs

class VideoBookmarkSerializer(serializers.ModelSerializer):

    class Meta:
        model = VideoBookmark
        fields = ["id", "video", "created_at"]

class AdminVideoCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Video
        exclude = (
            "uploaded_by",
            "status",
            "view_count",
            "download_count",
            "rejection_reason",
            "is_deleted",
            "created_at",
            "updated_at",
        )

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Doctor user not found.")

        if user.role != UserRole.DOCTOR:
            raise serializers.ValidationError(
                "Videos can only be created for doctor users."
            )

        return user

    def create(self, validated_data):
        doctor = validated_data.pop("user_id")

        video = Video.objects.create(
            uploaded_by=doctor,
            status=Status.PUBLISHED,
            **validated_data
        )
        if video.video_file:
            self._process_video(video)

        return video
    
    def _process_video(self, video):
        # ---- 1. Extract original extension ----
        original_name = video.video_file.name
        _, ext = os.path.splitext(original_name)

        if not ext:
            ext = ".mp4"  # fallback (rare edge case)

        # ---- 2. Download video from storage ----
        with default_storage.open(original_name, "rb") as f:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_video:
                for chunk in f.chunks():
                    temp_video.write(chunk)
                temp_video_path = temp_video.name
        
        # ---- 3. Generate thumbnail ----
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_thumb:
            temp_thumbnail_path = temp_thumb.name
        
        duration = generate_thumbnail_moviepy(
            temp_video_path,
            temp_thumbnail_path,
            time_in_seconds=1.0
        )
        
        # ---- 4. Save thumbnail back to S3 ----
        with open(temp_thumbnail_path, "rb") as thumb_file:
            thumbnail_name = f"videos/thumbnails/{uuid.uuid4()}.jpg"

            saved_path = default_storage.save(
                thumbnail_name,
                ContentFile(thumb_file.read())
            )

        # ---- 5. Update model ----
        video.thumbnail = saved_path
        if duration:
            video.duration_seconds = int(duration)

        video.save(update_fields=["thumbnail", "duration_seconds"])
        # ---- 6. Cleanup ----
        os.remove(temp_video_path)
        os.remove(temp_thumbnail_path)


#####################  Response Serializers #############################
class PaginatedVideosSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = VideoListSerializer(many=True)

class PaginatedVideosListResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = PaginatedVideosSerializer()
    success = serializers.BooleanField()