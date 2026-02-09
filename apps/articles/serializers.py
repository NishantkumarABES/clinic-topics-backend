from rest_framework import serializers
from apps.articles.models import Article, Bookmark


class ArticleListSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "article_type",
            "speciality",
            "authors",
            "institution",
            "upload_date",
            "view_count",
            "download_count",
            "status",
            "is_featured",
            "is_bookmarked",
        ]

    def get_is_bookmarked(self, obj):
        user = self.context.get("user")

        if not user or not user.is_authenticated:
            return False

        return Bookmark.objects.filter(
            user=user,
            article=obj
        ).exists()

class ArticleDetailSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = "__all__"

    def get_is_bookmarked(self, obj):
        user = self.context.get("user")

        if not user or not user.is_authenticated:
            return False

        return Bookmark.objects.filter(
            user=user,
            article=obj
        ).exists()

class BookmarkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bookmark
        fields = ["id", "article", "created_at"]


################### Response Serializers ###################
class ArticlePaginationSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ArticleListSerializer(many=True)


class ArticleListResponseSerializer(serializers.Serializer):
    details = serializers.CharField()
    data = ArticlePaginationSerializer()
    success = serializers.BooleanField()