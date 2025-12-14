from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Feedback


class UserRegisterForm(UserCreationForm):
    """
    User registration form with comprehensive validation:
    - First name, last name, username, email, phone, password, confirm password
    - Email format validation
    - Phone number validation (exactly 10 digits)
    - Password rules: min 8 chars, uppercase, lowercase, number
    - Password confirmation matching
    - Username and email uniqueness
    """
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        }),
        error_messages={
            'required': 'First name is required.'
        }
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        }),
        error_messages={
            'required': 'Last name is required.'
        }
    )
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        error_messages={
            'required': 'Username is required.',
            'unique': 'A user with that username already exists.'
        }
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        error_messages={
            'required': 'Email is required.',
            'invalid': 'Enter a valid email address.'
        }
    )
    
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit phone number'
        }),
        error_messages={
            'required': 'Phone number is required.'
        }
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password'
        }),
        error_messages={
            'required': 'Password is required.'
        }
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        }),
        error_messages={
            'required': 'Please confirm your password.'
        }
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name',
            'username', 'email', 'phone',
            'password1', 'password2',
        ]

    def clean_username(self):
        """Validate username uniqueness."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists. Please choose a different username.")
        return username

    def clean_email(self):
        """Validate email format and uniqueness."""
        email = self.cleaned_data.get('email')
        
        # Email format is automatically validated by EmailField
        # Check email uniqueness
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists. Please use a different email address.")
        
        return email

    def clean_phone(self):
        """Validate phone number is exactly 10 digits."""
        phone = self.cleaned_data.get('phone')
        
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        
        # Check if phone contains only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        
        # Check if phone is exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        return phone

    def clean_password1(self):
        """Validate password meets all requirements."""
        password1 = self.cleaned_data.get('password1')
        
        if not password1:
            raise forms.ValidationError("Password is required.")
        
        # Minimum 8 characters
        if len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # At least one uppercase letter
        if not any(c.isupper() for c in password1):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        # At least one lowercase letter
        if not any(c.islower() for c in password1):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        
        # At least one number
        if not any(c.isdigit() for c in password1):
            raise forms.ValidationError("Password must contain at least one number.")
        
        return password1

    def clean(self):
        """Validate password confirmation matches."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError({
                    'password2': "Passwords do not match. Please enter the same password in both fields."
                })
        
        return cleaned_data

    def save(self, commit=True):
        """
        Save user with USER role and hashed password.
        UserCreationForm's save() method handles password hashing automatically.
        """
        # Call parent save with commit=False to get user object
        # This will create the user instance and set the hashed password
        user = super().save(commit=False)
        
        # Set role to USER for user registration
        user.role = 'USER'
        
        # Ensure user is active (required for login)
        user.is_active = True
        
        # Ensure email is set (required field)
        if not user.email:
            user.email = self.cleaned_data.get('email', '')
        
        # Save the user if commit=True
        # Password is already hashed by UserCreationForm's save method
        if commit:
            user.save()
            # Save many-to-many relationships if any (UserCreationForm handles this)
            self.save_m2m()
        
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile information.
    Allows editing: first_name, last_name, email, phone
    Username and role are read-only.
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        }),
        error_messages={
            'required': 'First name is required.'
        }
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        }),
        error_messages={
            'required': 'Last name is required.'
        }
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        error_messages={
            'required': 'Email is required.',
            'invalid': 'Enter a valid email address.'
        }
    )
    
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit phone number',
            'maxlength': '10'
        }),
        error_messages={
            'required': 'Phone number is required.'
        }
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your address',
            'rows': 3
        })
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your city'
        })
    )
    
    state = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your state'
        })
    )
    
    pincode = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your pincode'
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-populate fields with current user data
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['email'].initial = self.instance.email
            self.fields['phone'].initial = self.instance.phone
            self.fields['address'].initial = self.instance.address or ''
            self.fields['city'].initial = self.instance.city or ''
            self.fields['state'].initial = self.instance.state or ''
            self.fields['pincode'].initial = self.instance.pincode or ''
    
    def clean_email(self):
        """Validate email format and uniqueness (excluding current user)."""
        email = self.cleaned_data.get('email')
        
        # Check email uniqueness, excluding current user
        if self.user and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("A user with that email already exists. Please use a different email address.")
        
        return email
    
    def clean_phone(self):
        """Validate phone number is exactly 10 digits."""
        phone = self.cleaned_data.get('phone')
        
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        
        # Check if phone contains only digits
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        
        # Check if phone is exactly 10 digits
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        return phone


class PasswordChangeForm(forms.Form):
    """
    Form for changing user password.
    Requires current password verification and validates new password rules.
    """
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password',
            'autocomplete': 'current-password'
        }),
        error_messages={
            'required': 'Current password is required.'
        }
    )
    
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        }),
        error_messages={
            'required': 'New password is required.'
        }
    )
    
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        }),
        error_messages={
            'required': 'Please confirm your new password.'
        }
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Verify current password is correct."""
        current_password = self.cleaned_data.get('current_password')
        
        if not current_password:
            raise forms.ValidationError("Current password is required.")
        
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        
        return current_password
    
    def clean_new_password1(self):
        """Validate new password meets all requirements."""
        new_password1 = self.cleaned_data.get('new_password1')
        
        if not new_password1:
            raise forms.ValidationError("New password is required.")
        
        # Minimum 8 characters
        if len(new_password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # At least one uppercase letter
        if not any(c.isupper() for c in new_password1):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        # At least one lowercase letter
        if not any(c.islower() for c in new_password1):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        
        # At least one number
        if not any(c.isdigit() for c in new_password1):
            raise forms.ValidationError("Password must contain at least one number.")
        
        return new_password1
    
    def clean(self):
        """Validate password confirmation matches."""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError({
                    'new_password2': "Passwords do not match. Please enter the same password in both fields."
                })
        
        return cleaned_data
    
    def save(self):
        """Update user password using Django's password hashing."""
        if self.user:
            self.user.set_password(self.cleaned_data['new_password1'])
            self.user.save()
        return self.user


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your feedback here...',
            })
        }