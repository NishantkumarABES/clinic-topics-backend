from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobPost
from apps.jobs.serializers import (
    JobPostCreateUpdateSerializer, JobPostListDetailSerializer,
)
from apps.jobs.constants import JobStatus


class JobPostCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = JobPostCreateUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                { "detail": str(e), "data" : None, "success" : False},
                status=status.HTTP_400_BAD_REQUEST
            )
        job = serializer.save()

        return Response(
            {
                "detail": "Job post created successfully.",
                "data": JobPostListDetailSerializer(job).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class MyJobPostListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = JobPost.objects.filter(
            created_by=request.user
        ).order_by("-created_at")

        serializer = JobPostListDetailSerializer(
            queryset, many=True
        )

        return Response(
            {
                "detail": "Job posts retrieved successfully.",
                "data": serializer.data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

class PublicJobPostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = JobPost.objects.filter(
            status=JobStatus.PUBLISHED,
            visibility=JobStatus.PUBLISHED,  # see note below
        ).order_by("-created_at")

        serializer = JobPostListDetailSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "detail": "Public job posts retrieved successfully.",
                "data": serializer.data,
                "success": True   
            },
            status=status.HTTP_200_OK
        )

class JobPostDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            job = JobPost.objects.get(pk=pk, status=JobStatus.PUBLISHED)
        except JobPost.DoesNotExist:
            return Response(
                {
                    "detail": "Job post not found.",
                    "data": None,
                    "success": False
                },
                status=status.HTTP_404_NOT_FOUND
            )


        serializer = JobPostListDetailSerializer(job)

        return Response(
            {
                "detail": "Job post retrieved successfully.",
                "data": serializer.data,
                "success": True
            },
            status=status.HTTP_200_OK
        )

