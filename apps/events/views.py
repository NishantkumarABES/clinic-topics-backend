from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics, filters
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q

from apps.events.models import Event
from apps.events.serializers import EventSerializer, EventCreateUpdateSerializer



# -----------------------------------
# Helper function to apply filters
# -----------------------------------

class EventFilterHelper:
    @staticmethod
    def filter_queryset(request, queryset):
        # Filtering
        status_param = request.query_params.get("status")
        event_type = request.query_params.get("event_type")
        specialization = request.query_params.get("specialization")
        format_param = request.query_params.get("format")
        is_featured = request.query_params.get("is_featured")

        if status_param:
            queryset = queryset.filter(status=status_param)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if specialization:
            queryset = queryset.filter(specialization=specialization)
        if format_param:
            queryset = queryset.filter(format=format_param)
        if is_featured:
            queryset = queryset.filter(is_featured=is_featured.lower() == "true")

        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(agenda__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get("ordering")
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset

# -----------------------------------
# List + Create
# -----------------------------------
class EventPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 50

class EventListCreateAPIView(APIView):
    pagination_class = EventPagination
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Event.objects.filter(is_active=True)
        queryset = EventFilterHelper.filter_queryset(request, queryset)

        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = EventSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        auto_schema=None,
        request_body=EventCreateUpdateSerializer,
        responses={201: EventSerializer}
    )
    def post(self, request):
        serializer = EventCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save()
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------
# Retrieve + Update (PUT / PATCH)
# -----------------------------------
class EventRetrieveUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, id):
        try:
            return Event.objects.get(id=id, is_active=True)
        except Event.DoesNotExist:
            return None

    def get(self, request, id):
        event = self.get_object(id)
        if not event:
            return Response({"detail": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventSerializer(event)
        return Response(serializer.data)

    @swagger_auto_schema(
        auto_schema=None,
        request_body=EventCreateUpdateSerializer,
        responses={200: EventSerializer}
    )
    def patch(self, request, id):
        event = self.get_object(id)
        if not event:
            return Response({"detail": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventCreateUpdateSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            event = serializer.save()
            return Response(EventSerializer(event).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
