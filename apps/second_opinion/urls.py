from django.urls import path
from apps.second_opinion.views import (
    CalculateChargesView, SecondOpinionRequestListCreateView, SecondOpinionRequestDetailView, CreateSecondOpinionPaymentView,
    VerifySecondOpinionPaymentView, AvailableDoctorsListView, DoctorSecondOpinionListView, DoctorSecondOpinionDetailView,
    DoctorStartReviewView, DoctorSubmitResponseView, SubmitDoctorRatingView, ApplyCouponView, AdminCreateCouponView, AdminUpdateCouponView,
    AdminCouponListView, AdminDeleteCouponView, DoctorDashboardView
)

urlpatterns = [
    # Doctor discovery
    path("doctors/", AvailableDoctorsListView.as_view(), name="available-doctors"),

    # Charge calculation
    path("calculate-charges/", CalculateChargesView.as_view(), name="calculate-charges"),

    # Second opinion requests
    path("requests/", SecondOpinionRequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<uuid:request_id>/", SecondOpinionRequestDetailView.as_view(), name="request-detail"),
    path("apply-coupon/", ApplyCouponView.as_view(), name="apply-coupon"),

    # Payment
    path("payment/create-order/", CreateSecondOpinionPaymentView.as_view(), name="payment-create-order"),
    path("payment/verify/", VerifySecondOpinionPaymentView.as_view(), name="payment-verify"),

    # Doctor side views
    path("doctor/dashboard/", DoctorDashboardView.as_view()),
    path("doctor/requests/", DoctorSecondOpinionListView.as_view()),
    path("doctor/requests/<uuid:doctor_request_id>/", DoctorSecondOpinionDetailView.as_view()),
    path("doctor/requests/<uuid:doctor_request_id>/start-review/", DoctorStartReviewView.as_view()),
    path("doctor/requests/<uuid:doctor_request_id>/submit-response/", DoctorSubmitResponseView.as_view()),
    path("doctor-ratings/submit/", SubmitDoctorRatingView.as_view()),

    # Admin coupon management
    path("admin/coupons/", AdminCouponListView.as_view(), name="admin-coupon-list"),
    path("admin/coupons/create/", AdminCreateCouponView.as_view(), name="admin-create-coupon"),
    path("admin/coupons/<uuid:coupon_id>/update/", AdminUpdateCouponView.as_view(), name="admin-update-coupon"),
    path("admin/coupons/<uuid:coupon_id>/delete/", AdminDeleteCouponView.as_view(), name="admin-delete-coupon"),
]
