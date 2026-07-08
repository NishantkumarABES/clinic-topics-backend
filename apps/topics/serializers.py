import os, tempfile, uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import serializers
from django.utils.timezone import now
from apps.topics.models import Topic, TopicComment
from apps.topics.constants import Mood
from apps.topics.services import TopicImageService
from apps.topics.services import generate_thumbnail_moviepy

class TopicListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "description",
            "source_url",
            "video_url",
            "publishing_time",
            "publish_status",
            "image"
        ]
    def get_image(self, obj):
        return obj.image
    def get_video_url(self, obj):
        return obj.video

class TopicDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_eamil_id = serializers.UUIDField(source="author.email", read_only=True)
    image = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "description",
            "source_url",
            "video_url",
            "image",
            "author_name",
            "author_eamil_id",
            "publishing_time",
        ]
    def get_image(self, obj):
        return obj.image
    def get_video_url(self, obj):
        return obj.video

class AdminTopicReadSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.full_name",
        read_only=True
    )
    author_email = serializers.EmailField(
        source="author.email",
        read_only=True
    )
    transcription = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "title_color",
            "description",
            "image",
            "source_url",
            "video_url",
            "publishing_time",
            "publish_status",
            "author_name",
            "author_email",
            "created_at",
            "updated_at",
            "transcription",
            "thumbnail",
            "duration_seconds"
        ]
        read_only_fields = fields
    
    def get_image(self, obj):
        return obj.image
    
    def get_transcription(self, obj):
        if hasattr(obj, 'transcription'):
            from apps.topics.serializers import TopicTranscriptionSerializer
            return TopicTranscriptionSerializer(obj.transcription).data
        return None
    
    def get_video_url(self, obj):
        return obj.video
    
    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        if obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None
    
    

class AdminTopicWriteSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_null=True)
    image_file = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Topic
        fields = [
            "title",
            "title_color",
            "description",
            "image_url",
            "image_file",
            "source_url",
            "publishing_time",
        ]

    def validate(self, attrs):
        if attrs.get("image_url") and attrs.get("image_file"):
            raise serializers.ValidationError(
                "Provide either image_url OR image_file — not both."
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["author"] = request.user
        
        image_url = validated_data.get("image_url")
        if image_url:
            promoted_url = TopicImageService.promote_image_to_topic(image_url)
            validated_data["image_url"] = promoted_url
        
        return Topic.objects.create(**validated_data)

    def update(self, instance, validated_data):

        # If new file → delete old file
        if validated_data.get("image_file") and instance.image_file:
            instance.image_file.delete(save=False)

        return super().update(instance, validated_data)

class ArticleExtractionSerializer(serializers.Serializer):
    url = serializers.URLField()
    mood = serializers.ChoiceField(
        choices=Mood.choices, required=False, default=Mood.NEUTRAL
    )

class TitleRefinementSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, trim_whitespace=True)
    mood = serializers.ChoiceField(
        choices=Mood.choices, required=False, default=Mood.NEUTRAL
    )

class CleanupImagesSerializer(serializers.Serializer):
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
    )

class DoctorTopicCreateSerializer(serializers.ModelSerializer):
    video_file = serializers.FileField(required=True, write_only=True)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Topic
        fields = [
            "title",
            "description",
            "video_file",
        ]

    # -----------------------------------------
    # VIDEO VALIDATION
    # -----------------------------------------

    def validate_video_file(self, value):
        max_size = 300 * 1024 * 1024  # 300MB limit

        if value.size > max_size:
            raise serializers.ValidationError(
                "Video size cannot exceed 300MB."
            )

        allowed_types = [
            "video/mp4",
            "video/mpeg",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-matroska",
        ]

        if hasattr(value, "content_type") and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Unsupported video format. Allowed: mp4, mpeg, mov, avi, mkv."
            )

        return value

    # -----------------------------------------
    # CREATE
    # -----------------------------------------

    def create(self, validated_data):
        request = self.context["request"]

        topic = Topic.objects.create(
            author=request.user,
            title=validated_data["title"],
            description=validated_data.get("description"),
            video_file=validated_data["video_file"],
            publish_status=False,
            publishing_time=now()
        )
        if topic.video_file:
            self._process_video(topic)

        return topic
    
    def _process_video(self, topic):
        # ---- 1. Extract original extension ----
        original_name = topic.video_file.name
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
            thumbnail_name = f"topics/thumbnails/{uuid.uuid4()}.jpg"

            saved_path = default_storage.save(
                thumbnail_name,
                ContentFile(thumb_file.read())
            )
        
        

        # ---- 5. Update model ----
        topic.thumbnail = saved_path
        if duration:
            topic.duration_seconds = int(duration)
        print("Duration updated successfully", topic.duration_seconds, duration)

        topic.save(update_fields=["thumbnail", "duration_seconds"])
        print("Video model updated successfully")
        # ---- 6. Cleanup ----
        os.remove(temp_video_path)
        os.remove(temp_thumbnail_path)

class TopicCreateSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Topic uploaded successfully and sent for admin approval.")
    data = AdminTopicReadSerializer()

class TopicFeedItemSerializer(serializers.ModelSerializer):
    """Serializer for topics in the feed with type discriminator"""
    type = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "type",
            "id",
            "title",
            "title_color",
            "description",
            "publishing_time",
            "publish_status",
            "image",
            "source_url",
            "video_url",
            "like_count",
            "comment_count",
            "is_liked",
            "comments",
            "thumbnail",
            "duration_seconds"
        ]

    def get_type(self, obj):
        return "topic"

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_comments(self, obj):
        # Return latest 3 comments only for feed
        comments = obj.comments.all()[:3]
        return TopicCommentSerializer(comments, many=True).data
    
    def get_video_url(self, obj):
        return obj.video
    
    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        if obj.thumbnail:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None
    

class AdvertisementFeedItemSerializer(serializers.Serializer):
    """Serializer for advertisements in the feed with type discriminator"""
    type = serializers.SerializerMethodField()
    id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.URLField()
    image = serializers.ImageField()

    def get_type(self, obj):
        return "advertisement"

class TopicTranscriptionSerializer(serializers.ModelSerializer):
    """Serializer for transcription data"""
    class Meta:
        model = None  # Will be set dynamically
        fields = [
            'id',
            'sonix_media_id',
            'status',
            'transcript_text',
            'transcript_srt',
            'summary_text',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.topics.models import TopicTranscription
        self.Meta.model = TopicTranscription

class TopicCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = TopicComment
        fields = [
            "id",
            "user",
            "user_name",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at", "user_name"]

class TopicCommentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = TopicComment
        fields = ["comment"]

    def create(self, validated_data):
        request = self.context["request"]
        topic = self.context["topic"]

        return TopicComment.objects.create(
            topic=topic,
            user=request.user,
            comment=validated_data["comment"]
        )
