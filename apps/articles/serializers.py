from rest_framework import serializers
from apps.articles.models import Article, Bookmark
from apps.articles.constants import Status
from apps.accounts.constants import UserRole

class ArticleListSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Article
        fields = [
            "id",
            "uploaded_by",
            "title",
            "article_type",
            "speciality",
            "authors",
            "institution",
            "publication_date",
            "year",
            "view_count",
            "download_count",
            "status",
            "is_bookmarked",

            "is_deleted",
            "abstract",
            "content",
        ]


    def get_is_bookmarked(self, obj):
        user = self.context.get("request").user
        if not user or not user.is_authenticated:
            return False
        return Bookmark.objects.filter(user=user, article=obj).exists()
    
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
            self.fields.pop("content", None)
            self.fields.pop("abstract", None)

class ArticleDetailSerializer(serializers.ModelSerializer):
    is_bookmarked = serializers.SerializerMethodField()
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Article
        fields = "__all__"

    def get_is_bookmarked(self, obj):
        user = self.context.get("request").user
        if not user or not user.is_authenticated:
            return False
        return Bookmark.objects.filter(user=user, article=obj).exists()

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

class ArticleCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Article
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

    # def validate_authors(self, value):
    #     if not isinstance(value, list) or len(value) == 0:
    #         raise serializers.ValidationError(
    #             "Authors must be a non-empty list."
    #         )
    #     return value

class ArticleUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Article
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

class ArticleReviewSerializer(serializers.ModelSerializer):

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
        model = Article
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

class BookmarkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bookmark
        fields = ["id", "article", "created_at"]

#####################  Response Serializers #############################

class PaginatedArticlesListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ArticleListSerializer(many=True)
