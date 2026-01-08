from rest_framework import serializers
from apps.topics.models import TopicCategory, Topic, TopicImage

class TopicImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicImage
        fields = ["id", "image"]

class TopicCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicCategory
        fields = ["id", "title", "image"]

class TopicListSerializer(serializers.ModelSerializer):
    category = TopicCategorySerializer(read_only=True)

    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "category",
            "format",
            "publishing_time",
        ]

class TopicDetailSerializer(serializers.ModelSerializer):
    category = TopicCategorySerializer(read_only=True)
    images = TopicImageSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.email", read_only=True)

    class Meta:
        model = Topic
        fields = [
            "id",
            "title",
            "description",
            "category",
            "topic_audience",
            "format",
            "external_url",
            "pdf",
            "video_url",
            "images",
            "author_name",
            "publishing_time",
        ]



class AdminTopicReadSerializer(serializers.ModelSerializer):
    pass

class AdminTopicWriteSerializer(serializers.ModelSerializer):
    pass

class ArticleExtractionSerializer(serializers.Serializer):
    url = serializers.URLField()

class CleanupImagesSerializer(serializers.Serializer):
    image_urls = serializers.ListField(
        child=serializers.URLField(),
        allow_empty=False,
    )