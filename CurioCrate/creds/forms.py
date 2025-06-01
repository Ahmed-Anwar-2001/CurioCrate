# creds/forms.py

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UserForm(forms.ModelForm):
    """
    A simple ModelForm to let users edit their username and email.
    Add or remove fields here as desired (e.g. first_name, last_name, etc.).
    """
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            # ("first_name", "last_name" if your User model has them)
        ]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500",
                "placeholder": "Username"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500",
                "placeholder": "Email address"
            }),
        }
        labels = {
            "username": "Username",
            "email": "Email Address",
        }
