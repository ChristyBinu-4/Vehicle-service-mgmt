from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):

    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()
    phone = forms.CharField(max_length=10)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'username', 'email', 'phone',
            'password1', 'password2',
        ]

    # PHONE VALIDATION
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    # EMAIL UNIQUE VALIDATION
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email
      
    def clean_password1(self):
      cleaned_data = super().clean()
      password1 = cleaned_data.get("password1")
      password2 = cleaned_data.get("password2")


      # Minimum 8 chars
      if len(password1) < 8:
          raise forms.ValidationError("Password must be at least 8 characters long.")

      # At least one uppercase
      if not any(c.isupper() for c in password1):
          raise forms.ValidationError("Password must contain at least one uppercase letter.")

      # At least one lowercase
      if not any(c.islower() for c in password1):
          raise forms.ValidationError("Password must contain at least one lowercase letter.")

      # At least one number
      if not any(c.isdigit() for c in password1):
          raise forms.ValidationError("Password must contain at least one number.")
  
      if password1 and password2 and password1 != password2:
        raise forms.ValidationError("Passwords do not match.")
      
      return password1

