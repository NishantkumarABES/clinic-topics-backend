from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from django.utils import timezone

from apps.jobs.models import JobPost, JobApplication
from apps.jobs.serializers import (
    JobListSerializer, JobDetailSerializer, JobCreateSerializer, JobUpdateSerializer, JobReviewSerializer, 
    JobApplySerializer, MyAppliedJobListSerializer, MyAppliedJobDetailSerializer, AdminApplicationListSerializer,
    AdminJobCreateSerializer, paginatedJobListResponseSerializer, paginatedJobApplicationListResponseSerializer,
    DoctorApplicationListSerializer, DoctorApplicationReviewSerializer, paginatedDoctorApplicationListResponseSerializer,
    DoctorApplicationDetailSerializer, AdminJobListSerializer
)
from core.permissions import IsDoctor, IsAdmin
from apps.jobs.constants import JobPostStatus, ApplyMethod


class JobPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class JobListView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={
            200: paginatedJobListResponseSerializer()
        },
        manual_parameters=[
            openapi.Parameter(
                "search",
                in_=openapi.IN_QUERY,
                description="Search by title, company, or speciality",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "speciality",
                in_=openapi.IN_QUERY,
                description="Filter by speciality",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "work_type",
                in_=openapi.IN_QUERY,
                description="Filter by workplace type",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def get(self, request):

        queryset = JobPost.objects.filter(
            status=JobPostStatus.PUBLISHED,
            is_deleted=False,
            application_deadline__gte=timezone.now().date()
        )

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        work_type = request.GET.get("work_type")
        

        if speciality:
            queryset = queryset.filter(speciality=speciality)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(company_name__icontains=search) |
                Q(specialty__icontains=search)
            )
        
        if work_type:
            queryset = queryset.filter(workplace_type=work_type)


        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = JobListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data).data
        return Response(
            {
                "detail": "Jobs fetched successfully.",
                "data": response, "success": True,
            }
        )

class JobDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]

    @swagger_auto_schema(
        responses={
            200: JobDetailSerializer()
        }
    )
    def get(self, request, pk):
        job = get_object_or_404(
            JobPost,
            id=pk,
            status=JobPostStatus.PUBLISHED,
            is_deleted=False
        )

        JobPost.objects.filter(pk=job.pk).update(
            views=F("views") + 1
        )

        job.refresh_from_db()

        serializer = JobDetailSerializer(job, context={"request": request})
        return Response({
            "detail": "Job details fetched.",
            "data": serializer.data,
            "success": True,
        })

class JobApplyView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=JobApplySerializer,
    )
    def post(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            status=JobPostStatus.PUBLISHED,
            is_deleted=False
        )

        if job.application_deadline < timezone.now().date():
            return Response(
                {"detail": "Application deadline passed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if job.status in [JobPostStatus.CLOSED, JobPostStatus.EXPIRED]:
            return Response(
                {"detail": "This job is no longer accepting applications."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if job.apply_method != ApplyMethod.PLATFORM:
            return Response(
                {"detail": "Applications are not accepted on platform."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if job.created_by == request.user:
            return Response(
                {"detail": "You cannot apply to your own job posting."},
                status=status.HTTP_400_BAD_REQUEST
            )


        if JobApplication.objects.filter(
            job=job,
            applicant=request.user
        ).exists():
            return Response(
                {"detail": "You already applied."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = JobApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = serializer.save(
            job=job, applicant=request.user
        )

        JobPost.objects.filter(pk=job.pk).update(
            applications_count=F("applications_count") + 1
        )

        return Response(
            {
                "detail": "Application submitted successfully.",
                "data": {"application_id": str(application.id)},
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )

class MyJobsView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={
            200: paginatedJobListResponseSerializer()
        }
    )
    def get(self, request):
        queryset = JobPost.objects.filter(
            created_by=request.user,
            is_deleted=False
        )

        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        work_type = request.GET.get("work_type")


        if speciality:
            queryset = queryset.filter(specialty=speciality)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(company_name__icontains=search) |
                Q(specialty__icontains=search)
            )
        
        if work_type:
            queryset = queryset.filter(workplace_type=work_type)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = JobListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data).data


        return Response({
            "detail" : "My Jobs fetched successfully.",
            "data" : response, "success" : True,
        })

class MyJobDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    @swagger_auto_schema(
        responses={
            200: JobDetailSerializer()
        }
    )
    def get(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            created_by=request.user,
            is_deleted=False
        )

        serializer = JobDetailSerializer(job, context={"request": request})
        return Response({
            "detail" : "Job details fetched.",
            "data" : serializer.data,
            "success" : True,
        })

class MyJobCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        request_body=JobCreateSerializer,
    )
    def post(self, request):
        serializer = JobCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Job saved as draft.",
                "data": None,
                "success": True,
            },
            status=status.HTTP_201_CREATED
        )

class MyJobUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def patch(self, request, pk):

        job = get_object_or_404(
            JobPost, id=pk,
            created_by=request.user,
        )

        # 🔐 State Guard
        if job.status != JobPostStatus.DRAFT:
            return Response(
                {
                    "detail": "Job cannot be edited once it is moved for review.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.is_deleted:
            return Response(
                {
                    "detail": "Deleted jobs cannot be edited.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = JobUpdateSerializer(
            job,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Job updated successfully.",
                "data": serializer.data,
                "success": True,
            }
        )

class MyJobDeleteView(APIView):
    """
    Soft delete a job post.
    Applications remain for audit purposes.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def delete(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            created_by=request.user,
        )

        if job.is_deleted:
            return Response(
                {
                    "detail": "Job already deleted.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.is_deleted = True
        job.save(update_fields=["is_deleted"])

        return Response(
            {
                "detail": "Job deleted successfully.",
                "data": None,
                "success": True,
            }
        )

class MyAppliedJobsView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={
            200: paginatedJobApplicationListResponseSerializer()
        }
    )
    def get(self, request):
        queryset = JobApplication.objects.filter(
            applicant=request.user
        ).select_related("job")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = MyAppliedJobListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "My job applications fetched successfully.",
            "data": response,
            "success": True,
        })

class MyAppliedJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: MyAppliedJobDetailSerializer()
        }
    )
    def get(self, request, pk):
        application = get_object_or_404(
            JobApplication,
            id=pk,
            applicant=request.user
        )

        serializer = MyAppliedJobDetailSerializer(application)
        return Response({
            "detail": "My Application details fetched.",
            "data": serializer.data,
            "success": True,
        })

class MyJobApplicationsView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={
            200: paginatedDoctorApplicationListResponseSerializer()
        }
    )
    def get(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            created_by=request.user,
            is_deleted=False
        )

        if job.apply_method != ApplyMethod.PLATFORM:
            return Response(
                {"detail": "Applications are not managed on platform."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = job.applications.select_related("applicant")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DoctorApplicationListSerializer(page, many=True)

        return Response({
            "detail": "Applications fetched successfully.",
            "data": paginator.get_paginated_response(serializer.data).data,
            "success": True,
        })

class MyJobApplicationsDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={
            200: DoctorApplicationDetailSerializer()
        }
    )
    def get(self, request, job_id, application_id):

        # Step 1: Ensure job belongs to doctor
        job = get_object_or_404(
            JobPost,
            id=job_id,
            created_by=request.user,
            is_deleted=False
        )

        # Optional: Consistency with list API
        if job.apply_method != ApplyMethod.PLATFORM:
            return Response(
                {"detail": "Applications are not managed on platform."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 2: Ensure application belongs to this job
        application = get_object_or_404(
            JobApplication.objects.select_related("applicant", "job"),
            id=application_id,
            job=job
        )

        serializer = DoctorApplicationDetailSerializer(application)

        return Response(
            {
                "detail": "Application details fetched.",
                "data": serializer.data,
                "success": True,
            }
        )

class ReviewApplicationView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    @swagger_auto_schema(
        request_body=DoctorApplicationReviewSerializer,
    )
    def patch(self, request, job_id, application_id):

        # 1️⃣ Ensure job belongs to doctor
        job = get_object_or_404(
            JobPost, id=job_id,
            created_by=request.user,
            is_deleted=False
        )

        # 2️⃣ Ensure application belongs to this job
        application = get_object_or_404(
            JobApplication.objects.select_related("job"),
            id=application_id, job=job
        )

        # 3️⃣ Prevent reviewing closed/expired jobs
        if job.status in [
            JobPostStatus.CLOSED,
            JobPostStatus.EXPIRED
        ]:
            return Response(
                {"detail": "Cannot review applications for closed/expired job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorApplicationReviewSerializer(
            application,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Application updated successfully.",
            "success": True,
        })

class CloseJobView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def patch(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            created_by=request.user,
            status=JobPostStatus.PUBLISHED
        )

        job.status = JobPostStatus.CLOSED
        job.save(update_fields=["status"])

        return Response({
            "detail": "Job closed successfully.",
            "success": True,
        })

############## Admin API ###################

class AdminJobListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={
            200: paginatedJobListResponseSerializer()
        },
        auto_schema=None,
        manual_parameters=[
            openapi.Parameter(
                "status",
                in_=openapi.IN_QUERY,
                description="Filter by status",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "search",
                in_=openapi.IN_QUERY,
                description="Search by title or company",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def get(self, request):
        queryset = JobPost.objects.all().order_by("-created_at")

        status_filter = request.GET.get("status")
        search = request.GET.get("search")
        speciality = request.GET.get("speciality")
        job_function = request.GET.get("job_function")


        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        if speciality:
            queryset = queryset.filter(specialty=speciality)

        if job_function:
            queryset = queryset.filter(job_function=job_function)


        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminJobListSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data).data

        return Response({
            "detail": "Jobs fetched successfully for admin.",
            "data": response,
            "success": True,
        })

class AdminJobDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={
            200: JobDetailSerializer()
        },
        auto_schema=None,
    )
    def get(self, request, pk):
        job = get_object_or_404(JobPost, id=pk)
        serializer = JobDetailSerializer(job, context={"request": request})
        return serializer.data

class AdminJobReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        request_body=JobReviewSerializer,
        responses={
            200: JobDetailSerializer()
        },
        auto_schema=None,
    )
    def patch(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            status__in=[
                JobPostStatus.IN_REVIEW,
                JobPostStatus.DRAFT
            ]
        )

        serializer = JobReviewSerializer(
            job,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Job review updated successfully.",
            "success": True,
        })

class MoveJobToReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        responses={
            200: JobDetailSerializer()
        },
        auto_schema=None,
    )
    def patch(self, request, pk):

        job = get_object_or_404(
            JobPost,
            id=pk,
            status=JobPostStatus.DRAFT
        )

        job.status = JobPostStatus.IN_REVIEW
        job.save(update_fields=["status"])

        return Response({
            "detail": "Job moved to in-review.",
            "success": True,
        })

class AdminJobCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        request_body=AdminJobCreateSerializer,
        responses={
            201: paginatedJobListResponseSerializer()
        },
        auto_schema=None,
    )
    def post(self, request):

        serializer = AdminJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = serializer.save()

        return Response({
            "detail": "Job created and published successfully.",
            "data": {"job_id": str(job.id)},
            "success": True,
        }, status=status.HTTP_201_CREATED)

class AdminJobUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        request_body=JobUpdateSerializer,
        responses={
            200: JobDetailSerializer()
        },
        auto_schema=None,
    )
    def patch(self, request, pk):

        job = get_object_or_404(JobPost, id=pk)

        if job.is_deleted:
            return Response(
                {
                    "detail": "Deleted jobs cannot be edited.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = JobUpdateSerializer(
            job,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Job updated successfully by admin.",
            "data": serializer.data,
            "success": True,
        })

class AdminApplicationListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = JobPagination

    @swagger_auto_schema(
        responses={200: paginatedDoctorApplicationListResponseSerializer()},
        auto_schema=None,
    )
    def get(self, request, job_id):

        # 1️⃣ Ensure job exists (even if deleted or any status)
        job = get_object_or_404(JobPost, id=job_id)

        # 2️⃣ Fetch applications for that job only
        queryset = JobApplication.objects.filter(
            job=job
        ).select_related("job", "applicant").order_by("-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminApplicationListSerializer(page, many=True)

        return Response(paginator.get_paginated_response(serializer.data).data)

