from rest_framework import serializers

from apps.videos.models import Video, VideoBookmark
from apps.accounts.constants import UserRole
from apps.accounts.models import User
from apps.videos.constants import Status

class VideoListSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Video
        fields = [
            "id",
            "uploaded_by",
            "title",
            "description",
            "speciality",
            "duration_seconds",
            "view_count",
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
            "is_deleted",
            "created_at",
            "updated_at",
        )

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

        return video


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