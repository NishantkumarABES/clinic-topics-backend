import json
from rest_framework import serializers
from apps.events.models import Event, EventSpeaker, EventImage


# ---------------------------
# Speaker Serializer
# ---------------------------

class EventSpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ["id", "name", "title", "bio", "image"]


# ---------------------------
# Event Image Serializer
# ---------------------------

class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ["id", "image", "created_at"]


# ---------------------------
# Main Event Serializer (Read)
# ---------------------------



class EventSerializer(serializers.ModelSerializer):
    speakers = EventSpeakerSerializer(many=True, read_only=True)
    images = EventImageSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = "__all__"


# ---------------------------
# Event Create / Update Serializer
# ---------------------------

class EventSpeakerInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ["name", "title", "bio", "image"]


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    speakers = EventSpeakerInputSerializer(many=True, required=False)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "event_type",
            "specialization",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "timezone",
            "format",
            "is_free",
            "registration_fee",
            "is_certificate_available",
            "agenda",
            "venue",
            "event_link",
            "is_featured",
            "speakers",
            "images",
        ]

    def create(self, validated_data):
        speakers_data = validated_data.pop("speakers", [])
        images_data = validated_data.pop("images", [])

        event = Event.objects.create(**validated_data)

        # Create speakers
        for speaker in speakers_data:
            EventSpeaker.objects.create(event=event, **speaker)

        # Create images
        for img in images_data:
            EventImage.objects.create(event=event, image=img)

        return event

    def update(self, instance, validated_data):
        speakers_data = validated_data.pop("speakers", None)
        images_data = validated_data.pop("images", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if speakers_data is not None:
            instance.speakers.all().delete()
            for speaker in speakers_data:
                EventSpeaker.objects.create(event=instance, **speaker)

        if images_data is not None:
            for img in images_data:
                EventImage.objects.create(event=instance, image=img)

        return instance


# ---------------------------
# Response Serializers
# ---------------------------

class StandardResponseSerializer(serializers.Serializer):
    """Standard response format for all API endpoints."""
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False, help_text="Response payload")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "EventsStandardResponseSerializer"

class EventResponseSerializer(serializers.Serializer):
    """Response for single event endpoints (create, retrieve, update)."""
    detail = serializers.CharField(help_text="Response message")
    data = EventSerializer(help_text="Event data")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "EventsEventResponseSerializer"

class EventListResponseSerializer(serializers.Serializer):
    """Response for paginated event list endpoint."""
    detail = serializers.CharField(help_text="Response message")
    count = serializers.IntegerField(help_text="Total number of events")
    next = serializers.CharField(allow_null=True, help_text="URL to next page")
    previous = serializers.CharField(allow_null=True, help_text="URL to previous page")
    results = EventSerializer(many=True, help_text="List of events")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "EventsEventListResponseSerializer"

