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
from apps.second_opinion.models import (
    SecondOpinionRequest, SecondOpinionDocument, SecondOpinionPayment, SecondOpinionDoctorRequest
)
from apps.second_opinion.serializers import (
    CalculateChargesSerializer, CalculateChargesResponseSerializer, CreateSecondOpinionRequestSerializer,
    SecondOpinionRequestListSerializer, SecondOpinionRequestDetailSerializer, CreatePaymentOrderSerializer,
    VerifyPaymentSerializer, DoctorBasicInfoSerializer, DoctorSecondOpinionListSerializer, DoctorSecondOpinionDetailSerializer, 
    DoctorStartReviewSerializer, DoctorSubmitResponseSerializer, DoctorRatingSerializer
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
        request_body=CalculateChargesSerializer,
        responses={
            200: CalculateChargesResponseSerializer,
            400: openapi.Response(description="Validation error"),
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
            "doctors": doctor_charges,
            "total_amount": str(total_amount),
            "currency": "INR",
            "success": True
        })

class SecondOpinionRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = SecondOpinionPagination

    @swagger_auto_schema(
        responses={
            200: SecondOpinionRequestListSerializer(many=True),
        },
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by payment status",
                type=openapi.TYPE_STRING
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
            queryset = queryset.filter(payment_status=status_filter)

        # Pagination
        paginator = self.pagination_class()
        paginated_requests = paginator.paginate_queryset(queryset, request)

        serializer = SecondOpinionRequestListSerializer(
            paginated_requests,
            many=True
        )

        response_data = paginator.get_paginated_response(serializer.data).data
        response_data["success"] = True
        return Response(response_data)

    @swagger_auto_schema(
        request_body=CreateSecondOpinionRequestSerializer,
        responses={
            201: SecondOpinionRequestDetailSerializer,
            400: openapi.Response(description="Validation error"),
        },
    )
    def post(self, request):
        """Create a new second opinion request."""
        serializer = CreateSecondOpinionRequestSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        second_opinion_request = serializer.save()

        # Handle document uploads if present
        documents = request.FILES.getlist("documents")
        document_types = request.data.getlist("document_types") if hasattr(request.data, 'getlist') else []
        document_descriptions = request.data.getlist("document_descriptions") if hasattr(request.data, 'getlist') else []

        for i, doc_file in enumerate(documents):
            file_type = document_types[i] if i < len(document_types) else "other"
            description = document_descriptions[i] if i < len(document_descriptions) else ""

            SecondOpinionDocument.objects.create(
                second_opinion_request=second_opinion_request,
                file=doc_file,
                file_name=doc_file.name,
                file_type=file_type,
                description=description
            )

        # Return created request
        response_serializer = SecondOpinionRequestDetailSerializer(
            second_opinion_request
        )

        return Response({
            **response_serializer.data,
            "success": True
        }, status=status.HTTP_201_CREATED)

class SecondOpinionRequestDetailView(APIView):
    """
    Get details of a specific second opinion request.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        responses={
            200: SecondOpinionRequestDetailSerializer,
            404: openapi.Response(description="Not found"),
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
                {"detail": "Second opinion request not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SecondOpinionRequestDetailSerializer(second_opinion_request)
        return Response({
            **serializer.data,
            "success": True
        })

class CreateSecondOpinionPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        request_body=CreatePaymentOrderSerializer,
        responses={
            201: openapi.Response(
                description="Payment order created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "razorpay_order_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                        "currency": openapi.Schema(type=openapi.TYPE_STRING),
                        "key_id": openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description="Validation error"),
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

        from django.conf import settings

        return Response({
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "payment_id": str(payment.id),
            "success": True
        }, status=status.HTTP_201_CREATED)

class VerifySecondOpinionPaymentView(APIView):
    """
    Verify payment after successful Razorpay transaction.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        request_body=VerifyPaymentSerializer,
        responses={
            200: openapi.Response(
                description="Payment verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    }
                )
            ),
            400: openapi.Response(description="Verification failed"),
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
            "second_opinion_request_id": str(second_opinion_request.id),
            "success": True
        })

class AvailableDoctorsListView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    pagination_class = SecondOpinionPagination

    @swagger_auto_schema(
        responses={
            200: DoctorBasicInfoSerializer(many=True),
        },
        manual_parameters=[
            openapi.Parameter(
                "specialization", openapi.IN_QUERY,
                description="Filter by specialization",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "search_terms", openapi.IN_QUERY,
                description="Search by name or specialization",
                type=openapi.TYPE_STRING
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
        response_data = paginator.get_paginated_response(serializer.data).data
        response_data["success"] = True
        return Response(response_data)
    

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
        responses={200: DoctorSecondOpinionListSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by request status",
                type=openapi.TYPE_STRING
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
        response = paginator.get_paginated_response(serializer.data).data
        response["success"] = True
        return Response(response)

class DoctorSecondOpinionDetailView(APIView):
    """
    Retrieve full details of a specific second opinion request for doctor.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={200: DoctorSecondOpinionDetailSerializer},
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
                {"detail": "Request not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorSecondOpinionDetailSerializer(doctor_request)
        return Response({**serializer.data, "success": True})

class DoctorStartReviewView(APIView):
    """
    Doctor marks a request as in-review.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        responses={200: openapi.Response(description="Marked as in-review")}
    )
    def patch(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.paid().get(
                id=doctor_request_id,
                doctor=request.user
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorStartReviewSerializer(
            data={},
            context={"doctor_request": doctor_request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Request marked as in-review",
            "success": True
        })

class DoctorSubmitResponseView(APIView):
    """
    Doctor submits final opinion.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    @swagger_auto_schema(
        request_body=DoctorSubmitResponseSerializer,
        responses={200: openapi.Response(description="Response submitted")}
    )
    def patch(self, request, doctor_request_id):
        try:
            doctor_request = SecondOpinionDoctorRequest.objects.paid().get(
                id=doctor_request_id,
                doctor=request.user
            )
        except SecondOpinionDoctorRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found", "success": False},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DoctorSubmitResponseSerializer(
            data=request.data,
            context={"doctor_request": doctor_request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "detail": "Response submitted successfully",
            "success": True
        })


class SubmitDoctorRatingView(APIView):
    """
    Patient submits rating for a doctor after completed second opinion.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    @swagger_auto_schema(
        request_body=DoctorRatingSerializer,
        responses={201: DoctorRatingSerializer}
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
                "rating": DoctorRatingSerializer(rating).data,
                "success": True
            },
            status=status.HTTP_201_CREATED
        )