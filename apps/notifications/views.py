from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer

class AdminNotificationSummary(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        unread_count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()

        latest = Notification.objects.filter(recipient=user)[:5]

        serializer = NotificationSerializer(latest, many=True)

        return Response({
            "success": True,
            "unread_count": unread_count,
            "latest": serializer.data
        })

class MarkAllNotificationsRead(APIView):
    permission_classes = [IsAuthenticated]

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

    def get(self, request):
        user = request.user
        queryset = Notification.objects.filter(recipient=user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)