from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.events.models import Event
from apps.events.constants import EventStatus
from core.permissions import IsAdmin


class EventsAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_events = Event.objects.count()
        upcoming_events = Event.objects.filter(status=EventStatus.UPCOMING).count()
        ongoing_events = Event.objects.filter(status=EventStatus.ONGOING).count()
        completed_events = Event.objects.filter(status=EventStatus.COMPLETED).count()

        data = {
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "ongoing_events": ongoing_events,
            "completed_events": completed_events,
        }
        return Response(data)
