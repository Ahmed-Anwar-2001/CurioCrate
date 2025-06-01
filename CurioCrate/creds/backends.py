from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Authenticate with email (case-insensitive) + password.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
            print(f"DEBUG (EmailBackend - authenticate): User found with email '{email}', ID: {user.pk}")
        except User.DoesNotExist:
            print(f"DEBUG (EmailBackend - authenticate): No user found with email '{email}'")
            return None
        # ensure it’s not disabled/staff etc:
        if user.check_password(password) and self.user_can_authenticate(user):
            print(f"DEBUG (EmailBackend - authenticate): Authentication successful for user ID: {user.pk}")
            return user
        print(f"DEBUG (EmailBackend - authenticate): Authentication failed for user ID: {user.pk}")
        return None

    def get_user(self, user_id):
        print(f"DEBUG (EmailBackend - get_user): Attempting to retrieve user with ID: {user_id}")
        try:
            user = User.objects.get(pk=user_id)
            print(f"DEBUG (EmailBackend - get_user): Successfully retrieved user with ID: {user.pk}, Email: {user.email}")
            return user
        except User.DoesNotExist:
            print(f"DEBUG (EmailBackend - get_user): No user found with ID: {user_id}")
            return None
        except Exception as e:
            print(f"DEBUG (EmailBackend - get_user): An error occurred: {e}")
            return None