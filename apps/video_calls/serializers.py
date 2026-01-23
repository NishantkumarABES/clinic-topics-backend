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


class UserCallStatusSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    role = serializers.CharField()
    active_call = VideoCallSessionSerializer(allow_null=True)


#########################   Response Serializers    #########################

class StandardResponseSerializer(serializers.Serializer):
    """Standard response format for simple success/error responses."""
    detail = serializers.CharField(help_text="Response message")
    data = serializers.JSONField(allow_null=True, required=False, help_text="Response data")
    success = serializers.BooleanField(help_text="Success status")

    class Meta:
        ref_name = "VideoCallsStandardResponseSerializer"


class AgoraDetailsSerializer(serializers.Serializer):
    """Agora SDK details for video call."""
    app_id = serializers.CharField(help_text="Agora App ID")
    channel_name = serializers.CharField(help_text="Agora channel name")
    token = serializers.CharField(help_text="Agora authentication token")
    uid = serializers.IntegerField(help_text="User ID for Agora")


class CallInitiateDataSerializer(serializers.Serializer):
    """Data returned when initiating a call."""
    id = serializers.UUIDField(help_text="Call session ID")
    channel_name = serializers.CharField(help_text="Call channel name")
    doctor = serializers.UUIDField(help_text="Doctor user ID")
    patient = serializers.UUIDField(help_text="Patient user ID")
    status = serializers.CharField(help_text="Call status")
    created_at = serializers.DateTimeField(help_text="Call creation timestamp")
    call_status = serializers.CharField(help_text="Call delivery status (push/websocket/offline)")
    receiver_id = serializers.UUIDField(help_text="Receiver user ID")
    agora = AgoraDetailsSerializer(help_text="Agora connection details")


class CallInitiateResponseSerializer(serializers.Serializer):
    """Response for call initiate endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = CallInitiateDataSerializer()
    success = serializers.BooleanField(help_text="Success status")


class CallTokenDataSerializer(serializers.Serializer):
    """Token data for joining a call."""
    app_id = serializers.CharField(help_text="Agora App ID")
    channel_name = serializers.CharField(help_text="Channel name")
    token = serializers.CharField(help_text="Agora token")
    uid = serializers.IntegerField(help_text="User ID")


class CallTokenResponseSerializer(serializers.Serializer):
    """Response for call token endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = CallTokenDataSerializer()
    success = serializers.BooleanField(help_text="Success status")


class UserCallStatusDataSerializer(serializers.Serializer):
    """User call status data."""
    id = serializers.UUIDField(help_text="User ID")
    full_name = serializers.CharField(help_text="User full name")
    email = serializers.EmailField(help_text="User email")
    phone = serializers.CharField(help_text="User phone")
    role = serializers.CharField(help_text="User role")
    is_online = serializers.BooleanField(help_text="Whether user is online")
    active_call = VideoCallSessionSerializer(allow_null=True, help_text="Active call details if any")


class UserCallStatusResponseSerializer(serializers.Serializer):
    """Response for user call status endpoint."""
    detail = serializers.CharField(help_text="Response message")
    data = UserCallStatusDataSerializer()
    success = serializers.BooleanField(help_text="Success status")
