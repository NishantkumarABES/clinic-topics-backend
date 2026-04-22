import os
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Q, Avg, Count, F, ExpressionWrapper, DurationField, DateTimeField
from django.utils import timezone

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from decimal import Decimal

from core.permissions import IsPatient, IsDoctor, IsAdmin
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401
from apps.second_opinion.constants import SecondOpinionStatus
from apps.second_opinion.models import (
    CouponUsage, SecondOpinionRequest, SecondOpinionPayment, SecondOpinionDoctorRequest, Coupon
)
from apps.second_opinion.serializers import (
    CalculateChargesSerializer, CreateSecondOpinionRequestSerializer,
    SecondOpinionRequestListSerializer, SecondOpinionRequestDetailSerializer, CreatePaymentOrderSerializer,
    VerifyPaymentSerializer, DoctorBasicInfoSerializer, DoctorSecondOpinionListSerializer, DoctorSecondOpinionDetailSerializer, 
    DoctorStartReviewSerializer, DoctorSubmitResponseSerializer, DoctorRatingSerializer, ApplyCouponSerializer,
    AdminCouponCreateSerializer, AdminCouponResponseSerializer, AdminCouponListSerializer, AdminCouponUpdateSerializer,
    # Response serializers
    AdminCouponListResponseSerializer, SecondOpinionRequestListResponseSerializer, CalculateChargesResponseSerializer,
    SecondOpinionRequestDetailResponseSerializer, PaymentOrderResponseSerializer, PaymentVerificationResponseSerializer,
    DoctorBasicInfoListResponseSerializer, DoctorSecondOpinionListResponseSerializer,
    DoctorSecondOpinionDetailResponseSerializer, StandardResponseSerializer, DoctorRatingResponseSerializer
)
from apps.second_opinion.constants import SecondOpinionPaymentStatus
from apps.accounts.models import User
from apps.accounts.constants import UserRole, UserState
from apps.report_template.models import ReportTemplate
from apps.notifications.services import create_user_notification
from external.razorpay.service import razorpay_service

class SecondOpinionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class CalculateChargesView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        tags=["Second Opinion - Patient"],
        request_body=CalculateChargesSerializer,
        responses={
            200: CalculateChargesResponseSerializer,
            400: BAD_REQUEST_400,
        },
    )
    def post(self, request):
        serializer = CalculateChargesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor_ids = serializer.validated_data["doctor_ids"]

        # Fetch doctors with profiles
        doctors = User.objects.filter(
            id__in=doctor_ids,
            role=UserRole.DOCTOR
        ).select_related("doctor_profile")

        # Calculate charges
        doctor_charges = []
        total_amount = Decimal("0.00")

        for doctor in doctors:
            fee = doctor.doctor_profile.premium_online_fee or Decimal("0.00")
            total_amount += fee
            doctor_charges.append({
                "id": str(doctor.id),
                "full_name": doctor.full_name,
                "specialization": doctor.doctor_profile.specialization,
                "consultation_fee": str(fee),
            })

        return Response({
            "detail": "Charges calculated successfully",
            "data": {
                "doctors": doctor_charges,
                "total_amount": str(total_amount),
                "currency": "INR"
            },
            "success": True
        })

class SecondOpinionRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = SecondOpinionPagination

    @swagger_auto_schema(
        operation_summary="List my second opinion requests",
        tags=["Second Opinion - Patient"],
        responses={
            200: SecondOpinionRequestListResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by status (submitted/in-review/completed/)",
                type=openapi.TYPE_STRING,
                enum=["submitted", "in-review", "completed"]
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY,
                description="Page number", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                "page_size", openapi.IN_QUERY,
                description="Items per page (max 50)", type=openapi.TYPE_INTEGER
            ),
        ],
    )
    def get(self, request):
        """List all second opinion requests for the patient."""
        queryset = SecondOpinionRequest.objects.filter(
            patient=request.user
        ).prefetch_related("doctor_requests")

        # Optional status filter
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Pagination
        paginator = self.pagination_class()
        paginated_requests = paginator.paginate_queryset(queryset, request)

        serializer = SecondOpinionRequestListSerializer(
            paginated_requests,
            many=True
        )

        paginated_response = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "Requests retrieved successfully",
            "data": paginated_response,
            "success": True
        })

    @swagger_auto_schema(
        operation_summary="Create second opinion request",
        tags=["Second Opinion - Patient"],
        consumes=["multipart/form-data"],
        request_body=None,  # Don't use serializer for swagger
        responses={
            201: SecondOpinionRequestDetailResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        serializer = CreateSecondOpinionRequestSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e), "data": None, "success": False
            })

        
        second_opinion_request = serializer.save()

        response_serializer = SecondOpinionRequestDetailSerializer(second_opinion_request)
        print("Created second opinion request with ID:", second_opinion_request.id)
        return Response({
            "detail": "Second opinion request created successfully",
            "data": response_serializer.data, "success": True
        }, status=201)

class SecondOpinionRequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Get second opinion request details",
        tags=["Second Opinion - Patient"],
        responses={
            200: SecondOpinionRequestDetailResponseSerializer,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request, request_id):
        """Get second opinion request details."""
        try:
            second_opinion_request = SecondOpinionRequest.objects.prefetch_related(
                "doctor_requests__doctor__doctor_profile",
                "documents"
            ).get(
                id=request_id,
                patient=request.user
            )
        except SecondOpinionRequest.DoesNotExist:
            return Response(
                {"detail": "Second opinion request not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SecondOpinionRequestDetailSerializer(second_opinion_request, context={"request": request})
        return Response({
            "detail": "Request retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class CreateSecondOpinionPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Create Razorpay payment order",
        tags=["Second Opinion - Payment"],
        request_body=CreatePaymentOrderSerializer,
        responses={
            201: PaymentOrderResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):
        """Create payment order for second opinion."""
        serializer = CreatePaymentOrderSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e), "data": None, "success": False
            })

        second_opinion_request = serializer.validated_data["_second_opinion_request"]
        coupon = serializer.validated_data.get("coupon")
        discount_amount = serializer.validated_data.get("discount_amount")
        final_amount = serializer.validated_data.get("final_amount")

        if coupon:
            second_opinion_request.coupon = coupon
            second_opinion_request.discount_amount = discount_amount
            second_opinion_request.final_amount = final_amount
            second_opinion_request.save(
                update_fields=["coupon", "discount_amount", "final_amount"]
            )
        # Convert amount to paise (smallest currency unit)
        amount = second_opinion_request.payable_amount
        amount_paise = int(amount * 100)

        coupon = second_opinion_request.coupon
        if coupon and not coupon.is_valid(second_opinion_request.total_amount):
            return Response({
                "detail": "Coupon is no longer valid",
                "data": None,
                "success": False
            }, status=400)

        # Create Razorpay order
        razorpay_order = razorpay_service.create_order(
            amount=amount_paise,
            currency="INR",
            receipt=f"so_{second_opinion_request.id}",
            notes={
                "second_opinion_request_id": str(second_opinion_request.id),
                "patient_id": str(request.user.id)
            }
        )

        # Create payment record
        payment, created = SecondOpinionPayment.objects.get_or_create(
            second_opinion_request=second_opinion_request,
            defaults={
                "razorpay_order_id": razorpay_order["id"],
                "amount": amount,
                "currency": "INR",
                "status": SecondOpinionPaymentStatus.PENDING
            }
        )

        # If payment already existed, update Razorpay order id
        if not created:
            payment.razorpay_order_id = razorpay_order["id"]
            payment.status = SecondOpinionPaymentStatus.PENDING
            payment.save(update_fields=["razorpay_order_id", "status"])

        return Response({
            "detail": "Payment order created successfully",
            "data": {
                "razorpay_order_id": razorpay_order["id"],
                "amount": amount_paise,
                "currency": "INR",
                "key_id": os.getenv("RAZOR_PAY_API_KEY"),
                "payment_id": str(payment.id)
            },
            "success": True
        }, status=status.HTTP_201_CREATED)

class VerifySecondOpinionPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Verify Razorpay payment",
        tags=["Second Opinion - Payment"],
        request_body=VerifyPaymentSerializer,
        responses={
            200: PaymentVerificationResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    @transaction.atomic
    def post(self, request):
        """Verify payment signature and update status."""
        serializer = VerifyPaymentSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        payment = serializer.validated_data["_payment"]
        razorpay_payment_id = serializer.validated_data["razorpay_payment_id"]
        razorpay_signature = serializer.validated_data["razorpay_signature"]

        # Verify signature
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id=payment.razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )

        if not is_valid:
            payment.status = SecondOpinionPaymentStatus.FAILED
            payment.failure_reason = "Signature verification failed"
            payment.save()

            return Response({
                "detail": "Payment verification failed",
                "data": None,
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update payment record
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = SecondOpinionPaymentStatus.COMPLETED
        payment.save()

        # Update second opinion request payment status
        second_opinion_request = payment.second_opinion_request
        second_opinion_request.payment_status = SecondOpinionPaymentStatus.COMPLETED
        second_opinion_request.save(update_fields=["payment_status"])

        coupon = second_opinion_request.coupon

        if coupon:
            coupon.used_count = F("used_count") + 1
            coupon.save(update_fields=["used_count"])
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user,
                second_opinion_request=second_opinion_request,
                discount_amount=second_opinion_request.discount_amount
            )
        
        # Send notifications to all assigned doctors AFTER successful payment
        doctor_requests = second_opinion_request.doctor_requests.all()

        for dr in doctor_requests:
            create_user_notification(
                recipient=dr.doctor,
                title="New Second Opinion Request",
                message=f"You have received a new second opinion request from {second_opinion_request.patient.full_name}.",
                data={
                    "type": "SECOND_OPINION_REQUEST",
                    "request_id": str(second_opinion_request.id),
                    "doctor_request_id": str(dr.id)
                }
            )

        return Response({
            "detail": "Payment verified successfully",
            "data": {
                "second_opinion_request_id": str(second_opinion_request.id)
            },
            "success": True
        })

class AvailableDoctorsListView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    pagination_class = SecondOpinionPagination

    @swagger_auto_schema(
        operation_summary="List available doctors",
        tags=["Second Opinion - Patient"],
        responses={
            200: DoctorBasicInfoListResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
        manual_parameters=[
            openapi.Parameter(
                "specialization", openapi.IN_QUERY,
                description="Filter by specialization (e.g., Cardiology, Neurology)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "search_terms", openapi.IN_QUERY,
                description="Search by doctor name or specialization",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY,
                description="Page number", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                "page_size", openapi.IN_QUERY,
                description="Items per page (max 50)", type=openapi.TYPE_INTEGER
            ),
        ],
    )
    def get(self, request):
        doctors = User.objects.filter(
            role=UserRole.DOCTOR, state = UserState.ACTIVE,
            doctor_profile__consultation_fee__gt=0,
            doctor_profile__premium_online_fee__gt=0
        ).select_related(
            "doctor_profile"
        ).annotate(
            avg_rating=Avg("ratings_received__rating"),
            total_ratings=Count("ratings_received")
        )
        # Optional specialization filter
        specialization = request.query_params.get("specialization")
        search_terms = request.query_params.get("search_terms")

        if specialization:
            doctors = doctors.filter(
                doctor_profile__specialization__icontains=specialization
            )
        if search_terms:
            doctors = doctors.filter(
                Q(full_name__icontains=search_terms) |
                Q(doctor_profile__specialization__icontains=search_terms)
            )
        paginator = self.pagination_class()
        paginated_doctors = paginator.paginate_queryset(doctors, request)
        serializer = DoctorBasicInfoSerializer(paginated_doctors, many=True)
        paginated_response = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "Doctors retrieved successfully",
            "data": paginated_response,
            "success": True
        })
    

# ===================== Doctor Side Views =====================

class DoctorSecondOpinionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class DoctorSecondOpinionListView(APIView):
    """
    List all paid second opinion requests assigned to the logged-in doctor.
    """
    permission_classes = [IsAuthenticated, IsDoctor]
    pagination_class = DoctorSecondOpinionPagination

    @swagger_auto_schema(
        operation_summary="List my assigned second opinion requests",
        tags=["Second Opinion - Doctor"],
        responses={
            200: DoctorSecondOpinionListResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
        manual_parameters=[
            openapi.Parameter(
                "status", openapi.IN_QUERY,
                description="Filter by request status",
                type=openapi.TYPE_STRING,
                enum=["pending", "in_review", "completed"]
            ),
            openapi.Parameter(
                "page", openapi.IN_QUERY,
                description="Page number", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                "page_size", openapi.IN_QUERY,
                description="Items per page (max 50)", type=openapi.TYPE_INTEGER
            ),
        ],
    )
    def get(self, request):
        queryset = SecondOpinionDoctorRequest.objects.paid().filter(
            doctor=request.user
        ).select_related(
            "second_opinion_request__patient"
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = DoctorSecondOpinionListSerializer(page, many=True)
        paginated_response = paginator.get_paginated_response(serializer.data).data
        return Response({
            "detail": "Requests retrieved successfully",
            "data": paginated_response,
            "success": True
        })

class DoctorSecondOpinionDetailView(APIView):
    """
    Retrieve full details of a specific second opinion request for doctor.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Get second opinion request details",
        tags=["Second Opinion - Doctor"],
        responses={
            200: DoctorSecondOpinionDetailResponseSerializer,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        },
    )
    def get(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.paid().select_related(
                "second_opinion_request__patient"
            ).prefetch_related(
                "second_opinion_request__documents"
            ).get(
                id=doctor_request_id,
                doctor=request.user
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        is_template_filled = ReportTemplate.objects.filter(
            doctor=request.user
        ).exists()

        serializer = DoctorSecondOpinionDetailSerializer(doctor_request)
        return Response({
            "detail": "Request retrieved successfully",
            "data": {
                **serializer.data,
                "is_report_template_filled": is_template_filled
            },
            "success": True
        })

class DoctorStartReviewView(APIView):
    """
    Doctor marks a request as in-review.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Start reviewing request",
        tags=["Second Opinion - Doctor"],
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        }
    )
    def patch(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.paid().get(
                id=doctor_request_id,
                doctor=request.user
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorStartReviewSerializer(
            data={},
            context={"doctor_request": doctor_request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e), "data": None, "success": False
            })

        serializer.save()
        doctor_request.second_opinion_request.status = SecondOpinionStatus.IN_REVIEW
        patient = doctor_request.second_opinion_request.patient
        create_user_notification(
            recipient=patient,
            title="Doctor Started Reviewing Your Case",
            message=f"Dr. {doctor_request.doctor.full_name} has started reviewing your second opinion request.",
            data={
                "type": "SECOND_OPINION_IN_REVIEW",
                "doctor_request_id": str(doctor_request.id)
            }
        )
        doctor_request.second_opinion_request.save(update_fields=["status"])
        return Response({
            "detail": "Request marked as in-review",
            "data": None,
            "success": True
        })

class DoctorSubmitResponseView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Submit final second opinion",
        tags=["Second Opinion - Doctor"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "findings",
                "observations",
                "medical_opinion",
                "answer_to_patient"
            ],
            properties={
                "findings": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Doctor's clinical findings"
                ),
                "observations": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Doctor's observations from records or reports"
                ),
                "medical_opinion": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Doctor's professional medical opinion"
                ),
                "answer_to_patient": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Direct answer to patient's question"
                ),
            }
        ),
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            404: NOT_FOUND_404,
            401: UNAUTHORIZE_401,
        }
    )
    def patch(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.paid().get(
                id=doctor_request_id,
                doctor=request.user
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found", "data": None, "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorSubmitResponseSerializer(
            data=request.data,
            context={"doctor_request": doctor_request}
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        patient = doctor_request.second_opinion_request.patient
        create_user_notification(
            recipient=patient,
            title="Your Second Opinion is Ready",
            message=f"Dr. {doctor_request.doctor.full_name} has submitted your medical opinion.",
            data={
                "type": "SECOND_OPINION_COMPLETED",
                "doctor_request_id": str(doctor_request.id)
            }
        )
        req = doctor_request.second_opinion_request

        if req.completed_count == req.doctors_count:
            req.status = SecondOpinionStatus.COMPLETED
            req.save(update_fields=["status"])

        return Response({
            "detail": "Response submitted successfully",
            "data": None,
            "success": True
        })

class SubmitDoctorRatingView(APIView):
    """
    Patient submits rating for a doctor after completed second opinion.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Rate a doctor",
        tags=["Second Opinion - Patient"],
        request_body=DoctorRatingSerializer,
        responses={
            201: DoctorRatingResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        }
    )
    def post(self, request):
        serializer = DoctorRatingSerializer(
            data=request.data,
            context={"request": request}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e), "data": None, "success": False
            })

        rating = serializer.save()

        return Response(
            {
                "detail": "Rating submitted successfully",
                "data": DoctorRatingSerializer(rating).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )

class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Apply coupon to calculate discounted price",
        tags=["Second Opinion - Patient"],
        request_body=ApplyCouponSerializer,
        responses={
            200: StandardResponseSerializer,
            400: BAD_REQUEST_400,
            401: UNAUTHORIZE_401,
        },
    )
    def post(self, request):

        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        coupon = serializer.validated_data["coupon"]
        total_amount = serializer.validated_data["total_amount"]
        discount_amount = serializer.validated_data["discount_amount"]
        final_amount = serializer.validated_data["final_amount"]

        return Response({
            "detail": "Coupon applied successfully",
            "data": {
                "coupon_code": coupon.code,
                "original_amount": str(total_amount),
                "discount_amount": str(discount_amount),
                "final_amount": str(final_amount),
                "currency": "INR"
            },
            "success": True
        })

class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        doctor = request.user
        now = timezone.now()
        today = now.date()

        queryset = SecondOpinionDoctorRequest.objects.paid().filter(
            doctor=doctor
        )

        # -----------------------------------
        # 1. Pending Cases
        # -----------------------------------
        pending_cases = queryset.filter(
            status__in=[
                SecondOpinionStatus.SUBMITTED,
                SecondOpinionStatus.IN_REVIEW
            ]
        ).count()

        # -----------------------------------
        # 2. Due Today (48-hour SLA logic)
        # -----------------------------------
        due_expr = ExpressionWrapper(
            F("created_at") + timedelta(hours=48),
            output_field=DateTimeField()
        )

        due_today = queryset.annotate(
            due_at=due_expr
        ).filter(
            due_at__date=today
        ).exclude(
            status=SecondOpinionStatus.COMPLETED
        ).count()

        # -----------------------------------
        # 3. Recent Assignments (TOP 3)
        # -----------------------------------
        recent_qs = queryset.select_related(
            "second_opinion_request__patient"
        ).order_by("-created_at")[:3]

        recent_assignments = [
            {
                "id": str(obj.id),
                "patient_name": obj.second_opinion_request.patient.full_name,
                "status": obj.status,
                "submitted_at": obj.created_at,
                "responded_at": obj.responded_at,
                "due_at": obj.created_at + timedelta(hours=48)
            }
            for obj in recent_qs
        ]

        # -----------------------------------
        # Turnaround Expression (Reusable)
        # -----------------------------------
        turnaround_expr = ExpressionWrapper(
            F("responded_at") - F("created_at"),
            output_field=DurationField()
        )

        def calculate_activity(qs):
            completed_qs = qs.filter(
                status=SecondOpinionStatus.COMPLETED
            )

            avg_turnaround = completed_qs.annotate(
                turnaround=turnaround_expr
            ).aggregate(
                avg_time=Avg("turnaround")
            )["avg_time"]

            avg_hours = (
                avg_turnaround.total_seconds() / 3600
                if avg_turnaround else 0
            )

            return {
                "cases_completed": completed_qs.count(),
                "avg_turnaround_hours": round(avg_hours, 2),
                "pending_reviews": qs.exclude(
                    status=SecondOpinionStatus.COMPLETED
                ).count()
            }

        # -----------------------------------
        # 4. Review Activity
        # -----------------------------------
        start_of_week = today - timedelta(days=today.weekday())

        weekly_qs = queryset.filter(
            created_at__date__gte=start_of_week
        )

        review_activity = {
            "this_week": calculate_activity(weekly_qs),
            "all_time": calculate_activity(queryset)
        }

        return Response({
            "detail": "Doctor dashboard data fetched successfully",
            "data": {
                "pending_cases": pending_cases,
                "due_today": due_today,
                "recent_assignments": recent_assignments,
                "review_activity": review_activity
            },
            "success": True
        })

# ===================== Admin Side Views for Coupon Management =====================

class AdminCouponPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class AdminCouponListView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = AdminCouponPagination

    @swagger_auto_schema(
        operation_summary="List all coupons",
        tags=["Admin - Coupons"],
        responses={200: AdminCouponListResponseSerializer},
        manual_parameters=[
            openapi.Parameter(
                "search",
                openapi.IN_QUERY,
                description="Search by coupon code",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "is_active",
                openapi.IN_QUERY,
                description="Filter by active status",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                "page_size",
                openapi.IN_QUERY,
                description="Items per page (max 50)",
                type=openapi.TYPE_INTEGER
            ),
        ],
    )
    def get(self, request):

        coupons = Coupon.objects.all().order_by("-created_at")

        search = request.query_params.get("search")
        is_active = request.query_params.get("is_active")

        if search:
            coupons = coupons.filter(code__icontains=search)

        if is_active is not None:
            coupons = coupons.filter(is_active=is_active.lower() == "true")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(coupons, request)

        serializer = AdminCouponListSerializer(page, many=True)

        paginated_response = paginator.get_paginated_response(serializer.data).data

        return Response({
            "detail": "Coupons retrieved successfully",
            "data": paginated_response,
            "success": True
        })

class AdminCreateCouponView(APIView):
    parser_classes = [FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_summary="Create coupon",
        tags=["Admin - Coupons"],
        request_body=AdminCouponCreateSerializer,
        responses={201: AdminCouponResponseSerializer}
    )
    def post(self, request):

        serializer = AdminCouponCreateSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e),
                "data": None,
                "success": False
            })

        coupon = serializer.save()

        return Response({
            "detail": "Coupon created successfully",
            "data": AdminCouponResponseSerializer(coupon).data,
            "success": True
        }, status=status.HTTP_201_CREATED)

class AdminUpdateCouponView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_summary="Update coupon",
        tags=["Admin - Coupons"],
        request_body=AdminCouponUpdateSerializer,
        responses={200: AdminCouponResponseSerializer}
    )
    def patch(self, request, coupon_id):

        try:
            coupon = Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            return Response({
                "detail": "Coupon not found",
                "data": None,
                "success": False
            }, status=404)

        serializer = AdminCouponUpdateSerializer(
            coupon,
            data=request.data,
            partial=True
        )

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "detail": str(e),
                "data": None,
                "success": False
            })

        serializer.save()

        return Response({
            "detail": "Coupon updated successfully",
            "data": AdminCouponResponseSerializer(coupon).data,
            "success": True
        })

class AdminDeleteCouponView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_summary="Delete coupon",
        tags=["Admin - Coupons"],
        responses={204: "No Content", 404: NOT_FOUND_404}
    )
    def delete(self, request, coupon_id):

        try:
            coupon = Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            return Response({
                "detail": "Coupon not found",
                "data": None,
                "success": False
            }, status=404)

        coupon.delete()

        return Response({
            "detail": "Coupon deleted successfully",
            "data": None,
            "success": True
        }, status=status.HTTP_204_NO_CONTENT)