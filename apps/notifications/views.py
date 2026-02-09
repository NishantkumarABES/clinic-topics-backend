from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationSerializer, MarkNotificationReadSerializer, NotificationListResponseSerializer
)

class AdminNotificationSummary(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        user = request.user

        unread_count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()

        latest = Notification.objects.filter(recipient=user)

        serializer = NotificationSerializer(latest, many=True)

        return Response({
            "success": True,
            "unread_count": unread_count,
            "latest": serializer.data
        })

class MarkAllNotificationsRead(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        user = request.user

        Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({"success": True})

class AdminNotificationListPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminNotificationList(APIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AdminNotificationListPagination  

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        user = request.user
        queryset = Notification.objects.filter(recipient=user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserNotificationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class UserNotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = UserNotificationPagination

    @swagger_auto_schema(
        responses={200: NotificationListResponseSerializer()}
    )
    def get(self, request):

        queryset = Notification.objects.filter(
            recipient=request.user
        )

        unread_count = queryset.filter(is_read=False).count()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = NotificationSerializer(page, many=True)

        paginated_data = paginator.get_paginated_response(serializer.data).data

        return Response({
            "detail": "Notifications retrieved successfully",
            "data": {
                "unread_count": unread_count,
                **paginated_data
            },
            "success": True
        })

class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=MarkNotificationReadSerializer,
        responses={200: NotificationListResponseSerializer()}
    )
    def post(self, request):
        serializer = MarkNotificationReadSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Notification marked as read",
            "data": None,
            "success": True
        })

class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: NotificationListResponseSerializer()}
    )
    def post(self, request):

        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )

        return Response({
            "detail": "All notifications marked as read",
            "data": None,
            "success": True
        })
