from django.urls import path
from CurioAgent.views import home
from .views import (
    SignupAPIView, SignupPageView,
    LoginAPIView, TokenRefreshAPIView, LoginPageView, VerifyEmailView
)

app_name = 'creds'

urlpatterns = [

    # Home
    path('', home, name='home'),

    # Signup
    path('api/signup/', SignupAPIView.as_view(), name='api-signup'),
    path('signup/', SignupPageView.as_view(), name='signup-page'),

    # Login (JWT)
    path('api/login/', LoginAPIView.as_view(), name='api-login'),
    path('api/token/refresh/', TokenRefreshAPIView.as_view(), name='token-refresh'),

    # Login page
    path('login/', LoginPageView.as_view(), name='login-page'),

    # Email verification
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
]
