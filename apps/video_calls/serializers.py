from rest_framework import serializers
from .models import VideoCallSession


class CallInitiateSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    patient_id = serializers.UUIDField()


class VideoCallSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCallSession
        fields = "__all__"

class CallTokenSerializer(serializers.Serializer):
    call_id = serializers.UUIDField()
