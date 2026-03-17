from django.db import transaction
from rest_framework import serializers
from apps.events.models import Event, EventSpeaker, EventImage

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

class EventSpeakerInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = ["name", "title", "bio", "image"]

def extract_speakers_from_request(request):
    speakers = []
    data = request.data

    index = 0
    while True:
        name = data.get(f"speakers[{index}][name]")
        title = data.get(f"speakers[{index}][title]")
        bio = data.get(f"speakers[{index}][bio]")
        image = request.FILES.get(f"speakers[{index}][image]")

        if name is None and title is None and bio is None and image is None:
            break

        speakers.append({
            "name": name,
            "title": title,
            "bio": bio,
            "image": image
        })

        index += 1

    return speakers

class EventCreateUpdateSerializer(serializers.ModelSerializer):
    speakers = EventSpeakerInputSerializer(many=True, required=False)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False
    )

    class Meta:
        model = Event
        fields = [
            "title", "description", "event_type", "specialization",
            "start_date", "end_date", "start_time", "end_time",
            "timezone", "format", "is_free", "registration_fee",
            "is_certificate_available", "agenda", "venue",
            "event_link", "is_featured", "speakers", "images",
        ]

    # ---------------------------
    # CREATE
    # ---------------------------
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        validated_data.pop("speakers", [])
        images_data = validated_data.pop("images", [])
        speakers_data = extract_speakers_from_request(request)
        event = Event.objects.create(**validated_data)

        # ✅ Speakers (DRF already parsed image correctly)
        for speaker in speakers_data:
            if not speaker.get("name"):
                continue
            EventSpeaker.objects.create(
                event=event,
                name=speaker.get("name"),
                title=speaker.get("title"),
                bio=speaker.get("bio"),
                image=speaker.get("image")  # ✅ direct
            )

        # ✅ Event Images
        for img in images_data:
            EventImage.objects.create(event=event, image=img)

        return event

    # ---------------------------
    # UPDATE
    # ---------------------------
    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        validated_data.pop("speakers", None)
        speakers_data = extract_speakers_from_request(request)
        images_data = validated_data.pop("images", None)

        # ✅ Update basic fields safely
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # ✅ Replace speakers
        if speakers_data:
            instance.speakers.all().delete()

            for speaker in speakers_data:
                if not speaker.get("name"):
                    continue

                EventSpeaker.objects.create(
                    event=instance,
                    name=speaker.get("name"),
                    title=speaker.get("title"),
                    bio=speaker.get("bio"),
                    image=speaker.get("image")
                )

        # ✅ Append images
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

