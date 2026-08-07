from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Auth
    path("register/",        views.RegisterView.as_view(),        name="auth-register"),
    path("login/",           views.AwaazTokenObtainView.as_view(), name="auth-login"),
    path("token/refresh/",   TokenRefreshView.as_view(),           name="auth-token-refresh"),
    path("logout/",          views.LogoutView.as_view(),           name="auth-logout"),

    # Profile
    path("me/",              views.MeView.as_view(),               name="auth-me"),
    path("change-password/", views.ChangePasswordView.as_view(),   name="auth-change-password"),

    # OTP / phone verification
    path("otp/send/",        views.SendOTPView.as_view(),          name="auth-otp-send"),
    path("otp/verify/",      views.VerifyOTPView.as_view(),        name="auth-otp-verify"),

    # Admin
    path("users/",           views.UserListView.as_view(),         name="auth-user-list"),
]
