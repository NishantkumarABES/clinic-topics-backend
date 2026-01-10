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

class EventCreateUpdateSerializer(serializers.ModelSerializer):
    speakers = EventSpeakerSerializer(many=True, required=False)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True
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
            "format",
            "is_free",
            "registration_fee",
            "certificate_available",
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

        for speaker in speakers_data:
            EventSpeaker.objects.create(event=event, **speaker)

        for img in images_data:
            EventImage.objects.create(event=event, image=img)

        return event

    def update(self, instance, validated_data):
        speakers_data = validated_data.pop("speakers", None)
        images_data = validated_data.pop("images", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace speakers if provided
        if speakers_data is not None:
            instance.speakers.all().delete()
            for speaker in speakers_data:
                EventSpeaker.objects.create(event=instance, **speaker)

        # Append new images if provided
        if images_data is not None:
            for img in images_data:
                EventImage.objects.create(event=instance, image=img)

        return instance




