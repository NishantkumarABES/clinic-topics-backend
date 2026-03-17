import json
from rest_framework import serializers
from apps.events.models import Event, EventSpeaker, EventImage


# ---------------------------
# Speaker Serializer
# ---------------------------

class EventSpeakerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = EventSpeaker
        fields = ["id", "name", "title", "bio", "image_url"]
    
    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


# ---------------------------
# Event Image Serializer
# ---------------------------

class EventImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = EventImage
        fields = ["id", "image_url", "created_at"]
    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None

# ---------------------------
# Main Event Serializer (Read)
# ---------------------------



class EventSerializer(serializers.ModelSerializer):
    speakers = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = "__all__"

    def get_speakers(self, obj):
        request = self.context.get("request")
        speakers = obj.speakers.all()
        return EventSpeakerSerializer(
            speakers, many=True, context={"request": request}
        ).data

    def get_images(self, obj):
        request = self.context.get("request")
        images = obj.images.all()
        return EventImageSerializer(
            images, many=True, context={"request": request}
        ).data

   


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
        request = self.context.get("request")

        speakers_raw = validated_data.pop("speakers", "[]")
        images_data = validated_data.pop("images", [])

        # ✅ Parse speakers JSON
        try:
            speakers_data = json.loads(speakers_raw)
        except Exception:
            raise serializers.ValidationError({"speakers": "Invalid JSON"})

        event = Event.objects.create(**validated_data)

        # ✅ Attach speaker images using index
        for index, speaker in enumerate(speakers_data):
            image = request.FILES.get(f"speaker_images_{index}")

            EventSpeaker.objects.create(
                event=event,
                name=speaker.get("name"),
                title=speaker.get("title"),
                bio=speaker.get("bio"),
                image=image  # ← correctly mapped
            )

        # ✅ Event images
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

