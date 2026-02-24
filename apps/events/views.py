from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q

from apps.events.models import Event
from apps.events.serializers import (
    EventSerializer, EventCreateUpdateSerializer, EventResponseSerializer, EventListResponseSerializer, 
)
from core.api_responses import NOT_FOUND_404
from apps.accounts.constants import UserRole



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

    @swagger_auto_schema(
        operation_description="List all events with pagination and filters",
        responses={
            200: EventListResponseSerializer,
        },
    )
    def get(self, request):
        queryset = Event.objects.filter(is_active=True)
        queryset = EventFilterHelper.filter_queryset(request, queryset)
        
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = EventSerializer(paginated_queryset, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "Events retrieved successfully",
            "data": response_data,
            "success": True
        })

    @swagger_auto_schema(
        request_body=EventCreateUpdateSerializer,
        responses={201: EventResponseSerializer},
        auto_schema=None
    )
    def post(self, request):
        serializer = EventCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_role = request.user.role
        if user_role not in [UserRole.ADMIN]:
            return Response(
                {"detail": "You do not have permission to perform this action", "data": None, "success": False},
                status=status.HTTP_403_FORBIDDEN
            )
        event = serializer.save()
        return Response(
            {
                "detail": "Event created successfully",
                "data": EventSerializer(event).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

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

    @swagger_auto_schema(
        operation_description="Retrieve a single event by ID",
        responses={
            200: EventResponseSerializer,
            404: NOT_FOUND_404,
        },
    )
    def get(self, request, id):
        event = self.get_object(id)
        if not event:
            return Response(
                {"detail": "Event not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EventSerializer(event)
        return Response({
            "detail": "Event retrieved successfully",
            "data": serializer.data,
            "success": True
        })

    @swagger_auto_schema(
        auto_schema=None,
        request_body=EventCreateUpdateSerializer,
        responses={200: EventResponseSerializer}
    )
    def patch(self, request, id):
        event = self.get_object(id)
        if not event:
            return Response(
                {"detail": "Event not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EventCreateUpdateSerializer(event, data=request.data, partial=True)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {"detail": str(first_error), "data": None, "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        event = serializer.save()
        event.status = event.calculate_status()
        event.save(update_fields=["status"])
        return Response({
            "detail": "Event updated successfully",
            "data": EventSerializer(event).data,
            "success": True
        })

