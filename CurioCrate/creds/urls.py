from django.urls import path
from CurioAgent.views import (home, upload_csv_view, chat_api_view)
from .views import (
    SignupAPIView, SignupPageView,
    LoginAPIView, TokenRefreshAPIView, LoginPageView, VerifyEmailView, LogoutView, profile_view, settings_view
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
    # Logout
    path("logout/", LogoutView.as_view(), name="logout"),

    # Profile & Settings
    path('profile/', profile_view, name='profile'),
    path('settings/', settings_view, name='settings'),

    # Email verification
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),

    # Ingest Data from CSV
    path('upload-trustpilot-csv/', upload_csv_view, name='upload_csv'),


    # Chat API
    path('api/chat/', chat_api_view, name='chat_api'),
]
