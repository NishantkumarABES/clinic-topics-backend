from rest_framework import serializers
from apps.topics.models import Topic

class TopicListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "publishing_time",
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