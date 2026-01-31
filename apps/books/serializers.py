from rest_framework import serializers
from apps.books.models import Book, Collection
from apps.books.constants import Status



class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("id", "name", "description")

class BookListSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()
    collections = CollectionSerializer(many=True, read_only=True)

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
            "specialty",
            "book_type",
            "description",
            "rating",
            "views",
            "downloads",
            "status",
            "is_editor_curated",
            "collections",
            "created_at",
        )

class BookDetailSerializer(BookListSerializer):
    file = serializers.FileField(read_only=True)

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + ("file",)

class BookUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = (
            "title",
            "authors",
            "publisher",
            "edition",
            "publication_year",
            "isbn",
            "specialty",
            "book_type",
            "description",
            "file",
            "copyright_status",
            "access_level",
        )

    def validate_publication_year(self, value):
        if value < 1900:
            raise serializers.ValidationError("Publication year must be >= 1900.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        return Book.objects.create(
            uploaded_by=user,
            status=Status.PENDING,
            **validated_data
        )

class BookReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("status", "is_editor_curated")

    def validate_status(self, value):
        if value not in [Status.APPROVED, Status.REJECTED]:
            raise serializers.ValidationError(
                "Status can only be approved or rejected."
            )
        return value

