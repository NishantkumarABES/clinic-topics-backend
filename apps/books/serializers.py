from rest_framework import serializers
from apps.books.models import Book, Collection, BookRating
from apps.books.constants import Status


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("id", "name", "description")

class BookListSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()
    collections = CollectionSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = (
            "id",
            "uploaded_by",
            "title",
            "authors",
            "publisher",
            "edition",
            "publication_year",
            "isbn",
            "speciality",
            "book_type",
            "description",
            "rating",
            "rating_count",
            "views",
            "downloads",
            "status",
            "rejection_reason",
            "is_editor_curated",
            "price",
            "collections",
            "file_url",   # dynamically removed for non-admins
            "is_deleted", # dynamically removed for non-admins
            "created_at",
        )

    def __init__(self, *args, **kwargs):
        """
        Remove file_url if the requester is NOT an admin.
        """
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        if not request or not request.user.is_staff:
            self.fields.pop("file_url", None)
            self.fields.pop("is_deleted", None)

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

class BookDetailSerializer(BookListSerializer):
    is_paid = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + ("is_paid", "my_rating")

    def get_is_paid(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        # Free book
        if obj.price == 0:
            return True

        return obj.purchases.filter(
            user=request.user,
            is_paid=True
        ).exists()
    
    def get_my_rating(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        rating = obj.ratings.filter(user=request.user).first()

        if not rating:
            return None

        return {
            "rating": rating.rating,
            "comment": rating.comment,
            "created_at": rating.created_at,
        }

class BookUploadSerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    class Meta:
        model = Book
        fields = (
            "title",
            "authors",
            "publisher",
            "edition",
            "publication_year",
            "isbn",
            "speciality",
            "book_type",
            "description",
            "file",
            "copyright_status",
            "access_level",
            "price",
        )

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class BookDownloadResponseSerializer(serializers.Serializer):
    download_url = serializers.URLField()

class BookReviewSerializer(serializers.ModelSerializer):
    REVIEW_STATUS_CHOICES = (
        (Status.APPROVED, "Approved"),
        (Status.REJECTED, "Rejected"),
    )

    status = serializers.ChoiceField(choices=REVIEW_STATUS_CHOICES)
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Book
        fields = ("status", "is_editor_curated", "rejection_reason")

    def validate(self, attrs):
        status_value = attrs.get("status")
        reason = attrs.get("rejection_reason")

        # ✅ Require reason when rejecting
        if status_value == Status.REJECTED and not reason:
            raise serializers.ValidationError(
                "Rejection reason is required when rejecting a book."
            )

        # ✅ Clear reason if approved
        if status_value == Status.APPROVED:
            attrs["rejection_reason"] = None

        return attrs

class CreateBookPurchaseSerializer(serializers.Serializer):
    book_id = serializers.UUIDField()

class VerifyBookPurchaseSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

class BookUpdateSerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(
        min_value=0, required=False,
    )

    class Meta:
        model = Book
        exclude = (
            "uploaded_by",
            "status",
            "rating",
            "views",
            "downloads",
            "rejection_reason",
            "created_at",
            "updated_at",
        )

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class BookRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookRating
        fields = ("rating", "comment")

    def create(self, validated_data):
        user = self.context["request"].user
        book = self.context["book"]

        rating_obj, created = BookRating.objects.update_or_create(
            user=user,
            book=book,
            defaults=validated_data
        )

        book.update_rating()

        return rating_obj

class BookRatingListSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = BookRating
        fields = (
            "id",
            "user",
            "rating",
            "comment",
            "created_at",
        )

########### Response Serializers ####################

class PaginatedBookListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = BookListSerializer(many=True)

class StandardResponseSerializer(serializers.Serializer):
    """Standard response wrapper for simple responses."""
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False, help_text="Response data")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "BooksStandardResponseSerializer"

