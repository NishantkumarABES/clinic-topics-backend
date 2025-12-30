from django.urls import path
from apps.accounts.views import (
    LogoutView, PhoneOTPRequestView, PhoneOTPVerifyView, PasswordResetRequestView, PasswordResetConfirmView,
    DeactivateAccountView, ReactivateAccountView, DeleteAccountView, EmailOTPRequestView, EmailOTPVerifyView, RegisterView, UserMeView,
    AdminUserListView, EmailLoginView, PhoneLoginView, SocialLoginView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("email/request-otp/", EmailOTPRequestView.as_view()),
    path("email/verify-otp/", EmailOTPVerifyView.as_view()),
    path("phone/request-otp/", PhoneOTPRequestView.as_view()),
    path("phone/verify-otp/", PhoneOTPVerifyView.as_view()),

    # path("register/patient/", PatientRegistrationView.as_view()),
    # path("register/doctor/", DoctorRegistrationView.as_view()),
    path("register/<str:role>/", RegisterView.as_view(), name="register"),

    # Unified login endpoint - supports email, phone, and social login
    path("login/email/", EmailLoginView.as_view(), name="login"),
    path("login/phone/", PhoneLoginView.as_view(), name="login"),
    path("login/social/", SocialLoginView.as_view(), name="login"),



    path("me/", UserMeView.as_view(), name="user-me"),
    path("logout/", LogoutView.as_view()),
    path("password/reset/", PasswordResetRequestView.as_view()),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view()),

    path("deactivate/", DeactivateAccountView.as_view()),
    path("reactivate/", ReactivateAccountView.as_view()),
    path("delete/", DeleteAccountView.as_view()),

    path("token/refresh/", TokenRefreshView.as_view()),

    # Admin endpoints
    path("admin/users/<str:role>", AdminUserListView.as_view(), name="admin-user-list"),
]