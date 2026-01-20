import os, uuid
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_yasg.utils import swagger_auto_schema

from external.agora.utils import generate_agora_token
from apps.video_calls.signals import send_call_signal, is_user_online
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from apps.video_calls.models import VideoCallSession
from apps.video_calls.serializers import (
    CallInitiateSerializer, VideoCallSessionSerializer, CallTokenSerializer, UserCallStatusSerializer
)
from apps.video_calls.constants import CallStatus
from apps.notifications.services import send_push_notification

class BaseCallActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_call(self, call_id):
        return get_object_or_404(VideoCallSession, id=call_id)

    def validate_participant(self, request, call):
        user = request.user
        if user != call.doctor and user != call.patient:
            return False
        return True

class CallInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=CallInitiateSerializer,
        responses={201: VideoCallSessionSerializer}
    )
    @transaction.atomic
    def post(self, request):
        serializer = CallInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor_id = serializer.validated_data["doctor_id"]
        patient_id = serializer.validated_data["patient_id"]

        try:
            doctor = User.objects.get(id=doctor_id, role=UserRole.DOCTOR)
        except User.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = User.objects.get(id=patient_id, role=UserRole.PATIENT)
        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_400_BAD_REQUEST)

        if doctor.id == patient.id:
            return Response({"error": "Doctor and patient cannot be same user"}, status=status.HTTP_400_BAD_REQUEST)

        caller = request.user
        if caller != doctor and caller != patient:
            return Response({"error": "You are not part of this call"}, status=status.HTTP_403_FORBIDDEN)

        receiver = patient if caller == doctor else doctor

        # Create Agora channel
        channel_name = f"call_{uuid.uuid4().hex}"
        if VideoCallSession.objects.filter(
            status=CallStatus.ACTIVE,
            doctor=doctor
        ).exists() or VideoCallSession.objects.filter(
            status=CallStatus.ACTIVE,
            patient=patient
        ).exists():
            return Response(
                {"error": "One of the participants is already in an active call"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create call session
        call_session = VideoCallSession.objects.create(
            channel_name=channel_name,
            doctor=doctor,
            patient=patient,
            status=CallStatus.INITIATED,
        )

        # ===== Presence-aware routing =====
        if is_user_online(str(receiver.id)):
            send_call_signal(
                user_id=str(receiver.id),
                data={
                    "event": "incoming_call",
                    "call_id": str(call_session.id),
                    "channel_name": call_session.channel_name,
                    "caller_id": str(caller.id),
                    "caller_name": caller.full_name
                }
            )
            call_status = "ringing"
            print(
                "send signal to the receiver"
            )

        else:
            send_push_notification(
                user=receiver,
                title="Incoming Call",
                body=f"{caller.full_name} is calling you",
                data={
                    "event": "incoming_call",
                    "call_id": str(call_session.id),
                    "channel_name": call_session.channel_name,
                    "caller_id": str(caller.id)
                }
            )
            call_status = "push_sent"


        response_data = VideoCallSessionSerializer(call_session).data
        response_data["call_status"] = call_status
        response_data["receiver_id"] = str(receiver.id)

        return Response(response_data, status=status.HTTP_201_CREATED)

class CallTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=CallTokenSerializer,
        responses={200: "OK"}
    )
    def post(self, request):
        serializer = CallTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        call_id = serializer.validated_data["call_id"]

        try:
            call_session = VideoCallSession.objects.get(id=call_id)
        except VideoCallSession.DoesNotExist:
            return Response(
                {"error": "Call session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user

        # Verify user is part of this call
        if user != call_session.doctor and user != call_session.patient:
            return Response(
                {"error": "You are not part of this call"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Agora UID must be integer
        # Convert UUID to stable int
        # agora_uid = abs(hash(str(user.id))) % (2**31)
        agora_uid = user.id.int % (2**31)


        token = generate_agora_token(
            channel_name=call_session.channel_name,
            uid=agora_uid
        )

        return Response({
            "app_id": os.getenv("AGORA_APP_ID"),
            "channel_name": call_session.channel_name,
            "token": token,
            "uid": agora_uid
        }, status=status.HTTP_200_OK)

class CallAcceptView(BaseCallActionView):
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response({"error": "Not part of this call"}, status=status.HTTP_403_FORBIDDEN)

        if call.status != CallStatus.INITIATED:
            return Response({"error": "Call cannot be accepted in current state"}, status=status.HTTP_400_BAD_REQUEST)

        # Update DB state
        call.status = CallStatus.ACTIVE
        call.started_at = timezone.now()
        call.save(update_fields=["status", "started_at"])

        # ---- FIX START ----
        # Notify the OTHER participant
        other_user = call.doctor if request.user == call.patient else call.patient

        if is_user_online(str(other_user.id)):
            send_call_signal(
                user_id=str(other_user.id),
                data={
                    "event": "call_accepted",
                    "call_id": str(call.id)
                }
            )
        else:
            send_push_notification(
                user=other_user,
                title="Call Accepted",
                body="Your call has been accepted",
                data={
                    "event": "call_accepted",
                    "call_id": str(call.id)
                }
            )

        return Response({"message": "Call accepted"}, status=status.HTTP_200_OK)

class CallRejectView(BaseCallActionView):
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response({"error": "Not part of this call"}, status=status.HTTP_403_FORBIDDEN)

        if call.status != CallStatus.INITIATED:
            return Response({"error": "Call cannot be rejected in current state"}, status=status.HTTP_400_BAD_REQUEST)

        # Update DB state
        call.status = CallStatus.REJECTED
        call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])

        other_user = call.doctor if request.user == call.patient else call.patient

        if is_user_online(str(other_user.id)):
            send_call_signal(
                user_id=str(other_user.id),
                data={
                    "event": "call_rejected",
                    "call_id": str(call.id)
                }
            )
        else:
            send_push_notification(
                user=other_user,
                title="Call Rejected",
                body="Your call was rejected",
                data={
                    "event": "call_rejected",
                    "call_id": str(call.id)
                }
            )

        return Response({"message": "Call rejected"}, status=status.HTTP_200_OK)

class CallEndView(BaseCallActionView):
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response({"error": "Not part of this call"}, status=status.HTTP_403_FORBIDDEN)

        if call.status != CallStatus.ACTIVE:
            return Response({"error": "Only active calls can be ended"}, status=status.HTTP_400_BAD_REQUEST)

        call.status = CallStatus.ENDED
        call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])

        for participant in [call.doctor, call.patient]:
            if is_user_online(str(participant.id)):
                send_call_signal(
                    user_id=str(participant.id),
                    data={"event": "call_ended", "call_id": str(call.id)}
                )
            else:
                send_push_notification(
                    user=participant,
                    title="Call Ended",
                    body="The call has ended",
                    data={"event": "call_ended", "call_id": str(call.id)}
                )

        return Response({"message": "Call ended"}, status=status.HTTP_200_OK)

class UserCallStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: UserCallStatusSerializer})
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get active or initiated call for this user
        active_call = VideoCallSession.objects.filter(
            status__in=[CallStatus.ACTIVE, CallStatus.INITIATED]
        ).filter(
            models.Q(doctor=user) | models.Q(patient=user)
        ).first()

        response_data = {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "is_online": is_user_online(str(user.id)),
            "active_call": VideoCallSessionSerializer(active_call).data if active_call else None
        }

        return Response(response_data, status=status.HTTP_200_OK)
