from django.urls import path
from apps.second_opinion.views import (
    CalculateChargesView,
    SecondOpinionRequestListCreateView,
    SecondOpinionRequestDetailView,
    CreateSecondOpinionPaymentView,
    VerifySecondOpinionPaymentView,
    AvailableDoctorsListView
)

urlpatterns = [
    # Doctor discovery
    path("doctors/", AvailableDoctorsListView.as_view(), name="available-doctors"),

    # Charge calculation
    path("calculate-charges/", CalculateChargesView.as_view(), name="calculate-charges"),

    # Second opinion requests
    path("requests/", SecondOpinionRequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<uuid:request_id>/", SecondOpinionRequestDetailView.as_view(), name="request-detail"),

    # Payment
    path("payment/create-order/", CreateSecondOpinionPaymentView.as_view(), name="payment-create-order"),
    path("payment/verify/", VerifySecondOpinionPaymentView.as_view(), name="payment-verify"),
]
