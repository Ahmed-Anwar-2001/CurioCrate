# creds/utils.py

from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

def send_verification_email(user):
    code = default_token_generator.make_token(user)
    user.verification_code_sent_at = timezone.now()
    user.save(update_fields=['verification_code_sent_at'])

    subject = "Your CurioCrate Verification Code"
    body = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Your verification code is:\n\n"
        f"    {code}\n\n"
        "Enter this code in the app to verify your email.\n\n"
        "– CurioCrate Team"
    )

    EmailMessage(subject, body, to=[user.email]).send(fail_silently=False)
