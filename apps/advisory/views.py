from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from apps.advisory.models import AdvisoryMember
from apps.advisory.serializers import (
    AdvisoryMemberReadSerializer,
    AdvisoryMemberWriteSerializer,
    AdvisoryPagination,
)


# ============================================
# ADMIN ENDPOINTS
# ============================================

class AdminAdvisoryListCreateAPIView(APIView):
    """Admin endpoint to list and create advisory members."""
    permission_classes = [IsAdminUser]
    pagination_class = AdvisoryPagination
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")

        queryset = AdvisoryMember.objects.all()

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(specialization__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = AdvisoryMemberReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response

    @swagger_auto_schema(auto_schema=None)
    def post(self, request):
        serializer = AdvisoryMemberWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Advisory member created successfully",
                "data": AdvisoryMemberReadSerializer(member).data
            },
            status=status.HTTP_201_CREATED
        )


class AdminAdvisoryUpdateDeleteAPIView(APIView):
    """Admin endpoint to update or delete advisory members."""
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, member_id):
        member = get_object_or_404(AdvisoryMember, id=member_id)

        serializer = AdvisoryMemberWriteSerializer(
            member,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Advisory member updated successfully",
                "data": AdvisoryMemberReadSerializer(member).data
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(auto_schema=None)
    def delete(self, request, member_id):
        member = get_object_or_404(AdvisoryMember, id=member_id)
        member.delete()

        return Response(
            {
                "success": True,
                "message": "Advisory member deleted successfully"
            },
            status=status.HTTP_200_OK
        )


class AdminAdvisoryAnalyticsAPIView(APIView):
    """Admin endpoint to get advisory analytics."""
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_members = AdvisoryMember.objects.count()
        active_members = AdvisoryMember.objects.filter(status="active").count()
        inactive_members = AdvisoryMember.objects.filter(status="inactive").count()

        return Response(
            {
                "success": True,
                "total_members": total_members,
                "active_members": active_members,
                "inactive_members": inactive_members,
            },
            status=status.HTTP_200_OK
        )


# ============================================
# USER ENDPOINTS (Authenticated Users)
# ============================================

class AdvisoryListAPIView(APIView):
    """List all active advisory members for authenticated users."""
    permission_classes = [IsAuthenticated]
    pagination_class = AdvisoryPagination

    @swagger_auto_schema(
        responses={200: AdvisoryMemberReadSerializer(many=True)}
    )
    def get(self, request):
        search = request.query_params.get("search")

        # Only return active members for regular users
        queryset = AdvisoryMember.objects.filter(status="active")

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(specialization__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = AdvisoryMemberReadSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["success"] = True
        return response


class AdvisoryDetailAPIView(APIView):
    """Get a single active advisory member for authenticated users."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: AdvisoryMemberReadSerializer()}
    )
    def get(self, request, member_id):
        # Only allow access to active members
        member = get_object_or_404(AdvisoryMember, id=member_id, status="active")

        serializer = AdvisoryMemberReadSerializer(member)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
