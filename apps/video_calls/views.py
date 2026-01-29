import os, uuid
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_yasg.utils import swagger_auto_schema

from external.agora.utils import generate_agora_token
from apps.video_calls.signals import is_user_online
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from apps.video_calls.models import VideoCallSession
from apps.video_calls.serializers import (
    CallInitiateSerializer, VideoCallSessionSerializer, CallTokenSerializer, UserCallStatusSerializer,
    # Response serializers
    StandardResponseSerializer, CallInitiateResponseSerializer, CallTokenResponseSerializer,
    UserCallStatusResponseSerializer
)
from apps.video_calls.constants import CallStatus
from apps.video_calls.dispatchers import dispatch_call_event
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401


class BaseCallActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_call(self, call_id):
        return get_object_or_404(VideoCallSession, id=call_id)

    def validate_participant(self, request, call):
        return request.user in [call.doctor, call.patient]

class CallInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Initiate a video call between doctor and patient",
        request_body=CallInitiateSerializer,
        responses={
            201: CallInitiateResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
        }
    )
    @transaction.atomic
    def post(self, request):
        serializer = CallInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor_id = serializer.validated_data["doctor_id"]
        patient_id = serializer.validated_data["patient_id"]

        doctor = get_object_or_404(User, id=doctor_id, role=UserRole.DOCTOR)
        patient = get_object_or_404(User, id=patient_id, role=UserRole.PATIENT)

        if doctor == patient:
            return Response(
                {"detail": "Doctor and patient cannot be same user", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        caller = request.user
        if caller not in [doctor, patient]:
            return Response(
                {"detail": "You are not part of this call", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        if VideoCallSession.objects.filter(
            status__in=[CallStatus.INITIATED, CallStatus.ACTIVE]
        ).filter(models.Q(doctor=caller) | models.Q(patient=caller)).exists():
            return Response(
                {"detail": "You already have an ongoing call", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        VideoCallSession.objects.select_for_update().filter(
            models.Q(doctor=doctor) | models.Q(patient=patient),
            status=CallStatus.ACTIVE
        )

        receiver = patient if caller == doctor else doctor
        channel_name = f"call_{uuid.uuid4().hex}"

        call_session = VideoCallSession.objects.create(
            channel_name=channel_name,
            doctor=doctor,
            patient=patient,
            status=CallStatus.INITIATED,
        )

        # Generate Agora token for caller immediately
        agora_uid = caller.id.int % (2**31)
        token = generate_agora_token(channel_name, agora_uid)
        
        # Send incoming call push to receiver
        event_data = {
            "event": "incoming_call",
            "call_id": str(call_session.id),
            "channel_name": channel_name,
            "caller_id": str(caller.id),
            "agora": {
                "app_id": os.getenv("AGORA_APP_ID"),
                "channel_name": channel_name,
                "token": token,
                "uid": agora_uid
            }
        }
        try:
            result = dispatch_call_event(receiver, event_data)
        except Exception as e:
            call_session.status = CallStatus.FAILED
            call_session.save(update_fields=["status"])
            return Response(
                {"detail": str(e), "data": None, "success": False}
            )

        response_data = VideoCallSessionSerializer(call_session).data
        response_data["call_status"] = result["via"]
        response_data["receiver_id"] = str(receiver.id)

        # Token bundle for caller
        response_data["agora"] = {
            "app_id": os.getenv("AGORA_APP_ID"),
            "channel_name": channel_name,
            "token": token,
            "uid": agora_uid
        }
        return Response(
            {"detail": "Call initiated successfully", "data": response_data, "success": True},
            status=status.HTTP_201_CREATED
        )

class CallTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate Agora token for joining a call",
        request_body=CallTokenSerializer,
        responses={
            200: CallTokenResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
            404: NOT_FOUND_404,
        }
    )
    def post(self, request):
        serializer = CallTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        call = get_object_or_404(VideoCallSession, id=serializer.validated_data["call_id"])

        if request.user not in [call.doctor, call.patient]:
            return Response(
                {"detail": "You are not part of this call", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        agora_uid = request.user.id.int % (2**31)
        token = generate_agora_token(call.channel_name, agora_uid)

        return Response({
            "detail": "Token generated successfully",
            "data": {
                "app_id": os.getenv("AGORA_APP_ID"),
                "channel_name": call.channel_name,
                "token": token,
                "uid": agora_uid
            },
            "success": True
        })

class CallAcceptView(BaseCallActionView):
    @swagger_auto_schema(
        operation_description="Accept an incoming call",
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
            404: NOT_FOUND_404,
        }
    )
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response(
                {"detail": "Not part of this call", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        if call.status != CallStatus.INITIATED:
            return Response(
                {"detail": "Call cannot be accepted", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        call.status = CallStatus.ACTIVE
        call.started_at = timezone.now()
        call.save(update_fields=["status", "started_at"])

        other = call.doctor if request.user == call.patient else call.patient

        dispatch_call_event(other, {"event": "call_accepted", "call_id": str(call.id)})

        return Response({"detail": "Call accepted", "data": None, "success": True})

class CallRejectView(BaseCallActionView):
    @swagger_auto_schema(
        operation_description="Reject an incoming call",
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400,
            404: NOT_FOUND_404,
        }
    )
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response(
                {"detail": "Not part of this call", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        if call.status != CallStatus.INITIATED:
            return Response(
                {"detail": "Call cannot be rejected", "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        call.status = CallStatus.REJECTED
        call.ended_at = timezone.now()
        call.save(update_fields=["status", "ended_at"])

        other = call.doctor if request.user == call.patient else call.patient

        dispatch_call_event(other, {"event": "call_rejected", "call_id": str(call.id)})

        return Response({"detail": "Call rejected", "data": None, "success": True})

class CallEndView(BaseCallActionView):
    @swagger_auto_schema(
        operation_description="End or cancel a call",
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400, 401: UNAUTHORIZE_401,
            403: BAD_REQUEST_400, 404: NOT_FOUND_404,
        }
    )
    def post(self, request, id):
        call = self.get_call(id)

        if not self.validate_participant(request, call):
            return Response(
                {"detail": "Not part of this call", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )

        # Case 1: Cancel before acceptance
        if call.status == CallStatus.INITIATED:
            call.status = CallStatus.ENDED
            call.ended_at = timezone.now()
            call.save(update_fields=["status", "ended_at"])

            other = call.doctor if request.user == call.patient else call.patient
            dispatch_call_event(other, {"event": "call_cancelled", "call_id": str(call.id)})
            return Response(
                {"detail": "Call cancelled successfully", "data": None, "success": True}
            )

        # Case 2: Normal active call end
        if call.status == CallStatus.ACTIVE:
            call.status = CallStatus.ENDED
            call.ended_at = timezone.now()
            call.save(update_fields=["status", "ended_at"])

            for participant in [call.doctor, call.patient]:
                dispatch_call_event(participant, {"event": "call_ended", "call_id": str(call.id)})

            return Response(
                {"detail": "Call ended successfully", "data": None, "success": True}
            )

        # Invalid state
        return Response(
            {"detail": "Call cannot be ended", "data": None, "success": False},
            status=status.HTTP_400_BAD_REQUEST
        )

class UserCallStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get user's call status and online status",
        responses={
            200: UserCallStatusResponseSerializer,
            401: UNAUTHORIZE_401,
            404: NOT_FOUND_404,
        }
    )
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        active_call = VideoCallSession.objects.filter(
            status__in=[CallStatus.ACTIVE, CallStatus.INITIATED]
        ).filter(models.Q(doctor=user) | models.Q(patient=user)).first()

        return Response({
            "detail": "User call status retrieved successfully",
            "data": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "is_online": is_user_online(str(user.id)),
                "active_call": VideoCallSessionSerializer(active_call).data if active_call else None
            },
            "success": True
        })
