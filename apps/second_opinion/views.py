import os
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import Q, Avg, Count

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from decimal import Decimal

from core.permissions import IsPatient, IsDoctor
from core.api_responses import BAD_REQUEST_400, NOT_FOUND_404, UNAUTHORIZE_401
from apps.second_opinion.constants import SecondOpinionStatus
from apps.second_opinion.models import (
    SecondOpinionRequest, SecondOpinionPayment, SecondOpinionDoctorRequest
)
from apps.second_opinion.serializers import (
    CalculateChargesSerializer, CreateSecondOpinionRequestSerializer,
    SecondOpinionRequestListSerializer, SecondOpinionRequestDetailSerializer, CreatePaymentOrderSerializer,
    VerifyPaymentSerializer, DoctorBasicInfoSerializer, DoctorSecondOpinionListSerializer, DoctorSecondOpinionDetailSerializer, 
    DoctorStartReviewSerializer, DoctorSubmitResponseSerializer, DoctorRatingSerializer,
    # Response serializers
    SecondOpinionRequestListResponseSerializer, CalculateChargesResponseSerializer,
    SecondOpinionRequestDetailResponseSerializer, PaymentOrderResponseSerializer, PaymentVerificationResponseSerializer,
    DoctorBasicInfoListResponseSerializer, DoctorSecondOpinionListResponseSerializer,
    DoctorSecondOpinionDetailResponseSerializer, StandardResponseSerializer, DoctorRatingResponseSerializer
)
from apps.second_opinion.constants import SecondOpinionPaymentStatus
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from external.razorpay.service import razorpay_service




class SecondOpinionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

class CalculateChargesView(APIView):
    """
    Calculate total consultation charges for selected doctors.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Calculate consultation charges",
        operation_description=(
            "Calculate total consultation charges for selected doctors.\n\n"
            "**Request Body:**\n"
            "- `doctor_ids`: List of doctor UUIDs to calculate fees for\n\n"
            "**Response includes:**\n"
            "- Individual doctor fees with their details\n"
            "- Total amount in INR"
        ),
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
        operation_description=(
            "Get all second opinion requests created by the logged-in patient.\n\n"
            "**Pagination:** Supports `page` and `page_size` query params.\n"
            "**Filter:** Use `status` param to filter by payment status (pending/completed/failed)."
        ),
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
        serializer.is_valid(raise_exception=True)
        second_opinion_request = serializer.save()

        response_serializer = SecondOpinionRequestDetailSerializer(second_opinion_request)
        return Response({
            "detail": "Second opinion request created successfully",
            "data": response_serializer.data,
            "success": True
        }, status=201)

class SecondOpinionRequestDetailView(APIView):
    """
    Get details of a specific second opinion request.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Get second opinion request details",
        operation_description=(
            "Retrieve full details of a specific second opinion request.\n\n"
            "**Response includes:**\n"
            "- Request details (complaint, history, status)\n"
            "- Assigned doctors with their response status\n"
            "- Uploaded documents\n"
            "- Doctor responses (if completed)"
        ),
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

        serializer = SecondOpinionRequestDetailSerializer(second_opinion_request)
        return Response({
            "detail": "Request retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class CreateSecondOpinionPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Create Razorpay payment order",
        operation_description=(
            "Create a Razorpay payment order for a second opinion request.\n\n"
            "**Flow:**\n"
            "1. Call this endpoint to get Razorpay order details\n"
            "2. Use `razorpay_order_id` and `key_id` to open Razorpay checkout\n"
            "3. After successful payment, call verify endpoint\n\n"
            "**Note:** Amount is returned in paise (multiply by 100)."
        ),
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
        serializer.is_valid(raise_exception=True)

        second_opinion_request = serializer.validated_data["_second_opinion_request"]

        # Convert amount to paise (smallest currency unit)
        amount_paise = int(second_opinion_request.total_amount * 100)

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
                "amount": second_opinion_request.total_amount,
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
    """
    Verify payment after successful Razorpay transaction.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        operation_summary="Verify Razorpay payment",
        operation_description=(
            "Verify payment after successful Razorpay transaction.\n\n"
            "**Call this after Razorpay checkout success callback.**\n\n"
            "**Request Body:**\n"
            "- `second_opinion_request_id`: The request being paid for\n"
            "- `razorpay_payment_id`: From Razorpay callback\n"
            "- `razorpay_signature`: From Razorpay callback\n\n"
            "**On success:** Request status changes to 'completed' and doctors are notified."
        ),
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
        operation_description=(
            "Get list of doctors available for second opinion consultations.\n\n"
            "**Response includes for each doctor:**\n"
            "- Name, specialization, consultation fee\n"
            "- Profile photo, years of experience\n"
            "- Average rating and total ratings count\n\n"
            "**Use filters to narrow down doctors by specialty or search terms.**"
        ),
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
            role=UserRole.DOCTOR, is_active=True
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
        operation_description=(
            "Get all paid second opinion requests assigned to the logged-in doctor.\n\n"
            "**Note:** Only shows requests where payment is completed.\n\n"
            "**Filter by status:**\n"
            "- `pending`: Waiting for doctor to start review\n"
            "- `in_review`: Doctor is currently reviewing\n"
            "- `completed`: Doctor has submitted response"
        ),
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
        operation_description=(
            "Retrieve full details of a specific second opinion request.\n\n"
            "**Response includes:**\n"
            "- Patient details (name, age, contact)\n"
            "- Chief complaint and medical history\n"
            "- All uploaded documents (reports, scans)\n"
            "- Current status of the request"
        ),
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

        serializer = DoctorSecondOpinionDetailSerializer(doctor_request)
        return Response({
            "detail": "Request retrieved successfully",
            "data": serializer.data,
            "success": True
        })

class DoctorStartReviewView(APIView):
    """
    Doctor marks a request as in-review.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Start reviewing request",
        operation_description=(
            "Mark a second opinion request as 'in-review'.\n\n"
            "**Call this when you start reviewing a patient's case.**\n\n"
            "**Transitions:** pending → in_review\n"
            "**Note:** Cannot be called if already in_review or completed."
        ),
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
        serializer.is_valid(raise_exception=True)
        serializer.save()
        doctor_request.second_opinion_request.status = SecondOpinionStatus.IN_REVIEW
        doctor_request.second_opinion_request.save(update_fields=["status"])
        return Response({
            "detail": "Request marked as in-review",
            "data": None,
            "success": True
        })

class DoctorSubmitResponseView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        operation_summary="Submit final second opinion",
        operation_description=(
            "Doctor submits their final structured medical response for a second opinion request.\n\n"
            "The response must contain four sections:\n"
            "- findings\n"
            "- observations\n"
            "- medical_opinion\n"
            "- answer_to_patient\n\n"
            "Request must be in `in_review` status."
        ),
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
        operation_description=(
            "Submit a rating for a doctor after completed second opinion.\n\n"
            "**Request Body:**\n"
            "- `doctor_id`: UUID of the doctor to rate\n"
            "- `second_opinion_request_id`: The completed request\n"
            "- `rating`: 1-5 stars\n"
            "- `review`: Optional text review\n\n"
            "**Note:** Can only rate doctors for completed second opinions."
        ),
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
        serializer.is_valid(raise_exception=True)
        rating = serializer.save()

        return Response(
            {
                "detail": "Rating submitted successfully",
                "data": DoctorRatingSerializer(rating).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )