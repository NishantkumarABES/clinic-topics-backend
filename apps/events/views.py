from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from apps.events.models import Event, EventRegistration
from apps.events.serializers import EventListSerializer, EventDetailSerializer


class EventListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        events = Event.objects.filter(is_active=True)

        event_type = request.query_params.get("type")
        is_paid = request.query_params.get("paid")

        if event_type:
            events = events.filter(event_type__slug=event_type)

        if is_paid is not None:
            events = events.filter(is_paid=is_paid.lower() == "true")

        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)

class EventDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id, is_active=True)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found"}, status=404)

        serializer = EventDetailSerializer(event)
        return Response(serializer.data)

class EventRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id, is_active=True)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found"}, status=404)

        registration, created = EventRegistration.objects.get_or_create(
            event=event,
            user=request.user
        )

        if not created:
            return Response(
                {"detail": "Already registered"},
                status=400
            )

        return Response({"message": "Registered successfully"})

