from rest_framework import serializers
from apps.events.models import Event, EventType


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ["id", "name", "slug"]

class EventListSerializer(serializers.ModelSerializer):
    event_type = EventTypeSerializer()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "event_type",
            "start_datetime",
            "end_datetime",
            "mode",
            "is_paid",
            "price",
            "is_certificate_available",
        ]

class EventDetailSerializer(serializers.ModelSerializer):
    event_type = EventTypeSerializer()

    class Meta:
        model = Event
        fields = "__all__"
