from rest_framework import serializers
from django.utils.timezone import now
from apps.topics.models import Topic
from apps.topics.services import TopicImageService

class TopicListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "description",
            "publishing_time",
            "publish_status",
            "image"
        ]
    def get_image(self, obj):
        return obj.image

class TopicDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_eamil_id = serializers.UUIDField(source="author.email", read_only=True)
    image = serializers.SerializerMethodField()
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
    

    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
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
        ]
        read_only_fields = fields
    
    def get_image(self, obj):
        return obj.image
    
    def get_transcription(self, obj):
        if hasattr(obj, 'transcription'):
            from apps.topics.serializers import TopicTranscriptionSerializer
            return TopicTranscriptionSerializer(obj.transcription).data
        return None

class AdminTopicWriteSerializer(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False, allow_null=True)
    image_file = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Topic
        fields = [
            "title",
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

class CleanupImagesSerializer(serializers.Serializer):
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
    )

class DoctorTopicCreateSerializer(serializers.ModelSerializer):
    video_url = serializers.URLField(write_only=True, required=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Topic
        fields = ["title", "description", "video_url"]

    def create(self, validated_data):
        request = self.context["request"]

        topic = Topic.objects.create(
            author=request.user,
            title=validated_data["title"],
            description=validated_data.get("description"),
            video_url=validated_data["video_url"],
            publish_status=False,
            publishing_time=now()
        )
        return topic

class TopicCreateSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Topic uploaded successfully and sent for admin approval.")
    data = AdminTopicReadSerializer()

class TopicFeedItemSerializer(serializers.ModelSerializer):
    """Serializer for topics in the feed with type discriminator"""
    type = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "type",
            "id",
            "title",
            "description",
            "publishing_time",
            "publish_status",
            "image",
            "video_url",
        ]

    def get_type(self, obj):
        return "topic"

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
