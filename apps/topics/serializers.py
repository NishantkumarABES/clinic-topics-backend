from rest_framework import serializers
from django.utils.timezone import now
from apps.topics.models import Topic
from external.cloudinary.utils import CloudinaryService

class TopicListSerializer(serializers.ModelSerializer):
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

class TopicDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_eamil_id = serializers.UUIDField(source="author.email", read_only=True)

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



class AdminTopicReadSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.full_name",
        read_only=True
    )
    author_email = serializers.EmailField(
        source="author.email",
        read_only=True
    )

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
        ]
        read_only_fields = fields

class AdminTopicWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = [
            "title",
            "description",
            "image",
            "source_url",
            "publishing_time",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["author"] = request.user
        return super().create(validated_data)

class ArticleExtractionSerializer(serializers.Serializer):
    url = serializers.URLField()

class CleanupImagesSerializer(serializers.Serializer):
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
    )

class DoctorTopicCreateSerializer(serializers.ModelSerializer):
    video_file = serializers.FileField(write_only=True)

    class Meta:
        model = Topic
        fields = ["title", "description", "video_file"]

    def create(self, validated_data):
        request = self.context["request"]
        video_file = validated_data.pop("video_file")

        # Cloudinary upload
        upload_response = CloudinaryService.upload_video(
            content=video_file,
            folder="topics/videos",
            public_id=f"topic_{request.user.id}_{now().timestamp()}"
        )

        video_url = upload_response["secure_url"]

        topic = Topic.objects.create(
            author=request.user,
            title=validated_data["title"],
            description=validated_data["description"],
            video_url=video_url,
            publish_status=False,
            publishing_time=now()
        )
        return topic

class TopicCreateSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Topic uploaded successfully and sent for admin approval.")
    data = AdminTopicReadSerializer()