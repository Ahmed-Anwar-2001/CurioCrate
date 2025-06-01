from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework import status
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import authenticate, login
from django.conf import settings

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .serializers import SignupSerializer, CustomTokenObtainPairSerializer

from .utils import send_verification_email

from CurioAgent.views import home

# --- API Signup (JSON) ---
class SignupAPIView(generics.GenericAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user, request)
        return Response(
            {"detail": "Signup successful. Check your email to verify."},
            status=status.HTTP_201_CREATED
        )

# --- Signup Page (GET + POST) ---
class SignupPageView(View):
    template_name = 'auth/signup.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        serializer = SignupSerializer(
            data=request.POST,
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            # send email with token
            send_verification_email(user)
            # stash email in session for the next step
            request.session['pending_verification_email'] = user.email
            return redirect('creds:verify-email')
        # show errors
        for field, errs in serializer.errors.items():
            for err in errs:
                messages.error(request, f"{field}: {err}")
        return render(request, self.template_name, {'data': request.POST})



User = get_user_model()
class VerifyEmailView(View):
    template_name = 'auth/verify_email.html'
    RESEND_TIMEOUT = 60  # seconds

    def get(self, request, *args, **kwargs):
        email = request.session.get('pending_verification_email')
        if not email:
            return redirect('creds:signup-page')
        request.session.setdefault('code_sent_at', 0)
        return render(request, self.template_name, {
            'email': email,
            'timeout': self.RESEND_TIMEOUT,
            'sent_at': request.session['code_sent_at'],
        })

    def post(self, request, *args, **kwargs):
        email = request.session.get('pending_verification_email')
        if not email:
            return redirect('creds:signup-page')

        # Resend flow
        if 'resend' in request.POST:
            user = User.objects.get(email=email)
            send_verification_email(user, request)
            request.session['code_sent_at'] = int(time.time())
            messages.info(request, "Verification code resent.")
            return redirect('creds:verify-email')

        # Verify code flow
        code = request.POST.get('code', '').strip()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Unknown session—please sign up again.")
            return redirect('creds:signup-page')

        if default_token_generator.check_token(user, code):
            # ← mark the user verified and active
            user.is_verified = True
            user.is_active   = True
            user.save(update_fields=['is_verified', 'is_active'])

            # clear session
            request.session.pop('pending_verification_email', None)

            messages.success(request, "Email verified! You can now log in.")
            return redirect('creds:login-page')
        else:
            messages.error(request, "Invalid or expired code. Try again.")
            return render(request, self.template_name, {
                'email': email,
                'timeout': self.RESEND_TIMEOUT,
                'sent_at': request.session.get('code_sent_at', 0),
            })

class LoginAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class TokenRefreshAPIView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]



User = get_user_model()

class LoginPageView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "auth/login.html")

    def post(self, request, *args, **kwargs):
        email       = request.POST.get("email")
        password    = request.POST.get("password")
        remember_me = request.POST.get("remember_me") == "on"

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        if user is None or not user.check_password(password):
            messages.error(request, "Invalid email or password.")
            return render(request, "auth/login.html", status=401)

        if not user.is_verified:
            messages.warning(request,
                "You need to verify your email address before you can log in.")
            return redirect("/verify-email/")

        if not user.is_active:
            messages.error(request, "Your account is inactive. Contact support.")
            return render(request, "auth/login.html", status=403)

        # OK, session login
        user.backend = 'creds.backends.EmailBackend'
        login(request, user)
        request.session.set_expiry(1209600 if remember_me else 0)
        return redirect("creds:home")




class LogoutView(View):
    def get(self, request, *args, **kwargs):
        # Log the user out and redirect to the login page (or homepage)
        logout(request)
        return redirect("creds:login-page")


@login_required
def profile_view(request):
    """
    Show the currently logged-in user’s profile information.
    """
    # request.user is guaranteed to be a valid User (since @login_required is applied)
    context = {
        'user': request.user,
    }
    return render(request, "chat_interface/profile.html", context)



from .forms import UserForm

@login_required
def settings_view(request):
    """
    Let a logged-in user edit their profile (username & email).
    """
    user = request.user

    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("creds:settings")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        # GET: prepopulate with current user data
        form = UserForm(instance=user)

    return render(request, "chat_interface/settings.html", {"form": form})
