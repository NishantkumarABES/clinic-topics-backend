from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.advertisements.models import Advertisement
from apps.advertisements.serializers import AdvertisementSerializer, AdvertisementListSerializer
from core.permissions import IsAdmin


class AdvertisementPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdvertisementCreateView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Create a new advertisement",
        request_body=AdvertisementSerializer,
        responses={
            201: openapi.Response(
                description="Advertisement created successfully",
                schema=AdvertisementSerializer,
            ),
            400: openapi.Response(
                description="Invalid data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
        },
        auto_schema=None
    )
    def post(self, request):
        serializer = AdvertisementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Advertisement created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {
                "success": False,
                "message": "Failed to create advertisement",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class AdvertisementUpdateView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Update an advertisement",
        request_body=AdvertisementSerializer,
        responses={
            200: openapi.Response(
                description="Advertisement updated successfully",
                schema=AdvertisementSerializer,
            ),
            404: openapi.Response(
                description="Advertisement not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: openapi.Response(
                description="Invalid data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
        },
        auto_schema=None
    )
    def patch(self, request, pk):
        try:
            advertisement = Advertisement.objects.get(pk=pk)
        except Advertisement.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Advertisement not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AdvertisementSerializer(
            advertisement,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Advertisement updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "success": False,
                "message": "Failed to update advertisement",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class AdvertisementListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = AdvertisementPagination

    @swagger_auto_schema(
        operation_description="List all advertisements with optional search and filters",
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Search by title or URL",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by status (enabled/disabled)",
                type=openapi.TYPE_STRING,
                enum=['enabled', 'disabled'],
                required=False,
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of items per page",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Advertisements retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "next": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "previous": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                    },
                ),
            ),
        },
        auto_schema=None
    )
    def get(self, request):
        # Get query parameters
        search_query = request.query_params.get('search', None)
        status_filter = request.query_params.get('status', None)

        # Start with all advertisements
        queryset = Advertisement.objects.all()

        # Apply search filter (search by title or URL)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(url__icontains=search_query)
            )

        # Apply status filter
        if status_filter:
            if status_filter.lower() in ['enabled', 'disabled']:
                queryset = queryset.filter(status=status_filter.lower())

        # Paginate results
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        # Serialize data
        serializer = AdvertisementListSerializer(paginated_queryset, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['success'] = True
        # Return paginated response
        return Response(response_data, status=status.HTTP_200_OK)


class AdvertisementDetailView(APIView):
    permission_classes = [IsAdmin]

    @swagger_auto_schema(
        operation_description="Get advertisement details",
        responses={
            200: openapi.Response(
                description="Advertisement retrieved successfully",
                schema=AdvertisementSerializer,
            ),
            404: openapi.Response(
                description="Advertisement not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
        },
        auto_schema=None
    )
    def get(self, request, pk):
        try:
            advertisement = Advertisement.objects.get(pk=pk)
            serializer = AdvertisementSerializer(advertisement)
            return Response(
                {
                    "success": True,
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Advertisement.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Advertisement not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Delete an advertisement",
        responses={
            204: openapi.Response(
                description="Advertisement deleted successfully",
            ),
            404: openapi.Response(
                description="Advertisement not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
        },
        auto_schema=None
    )
    def delete(self, request, pk):
        try:
            advertisement = Advertisement.objects.get(pk=pk)
            advertisement.delete()
            return Response(
                {
                    "success": True,
                    "message": "Advertisement deleted successfully"
                },
                status=status.HTTP_204_NO_CONTENT
            )
        except Advertisement.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Advertisement not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )
