from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "data",
            "is_read",
            "created_at",
            "read_at",
        ]

class MarkNotificationReadSerializer(serializers.Serializer):
    notification_id = serializers.UUIDField()

    def validate_notification_id(self, value):
        user = self.context["request"].user

        try:
            notification = Notification.objects.get(
                id=value,
                recipient=user
            )
        except Notification.DoesNotExist:
            raise serializers.ValidationError("Notification not found")

        self.notification = notification
        return value

    def save(self):
        self.notification.mark_read()
        return self.notification

class NotificationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    success = serializers.BooleanField()
