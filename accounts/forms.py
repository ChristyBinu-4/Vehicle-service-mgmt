from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Feedback, Diagnosis, WorkProgress


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
            # Disable email field
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['disabled'] = True
    
    def clean_email(self):
        """Email is non-editable, return existing email."""
        # Email should not be changed, return the existing email
        if self.instance and self.instance.pk:
            return self.instance.email
        return self.cleaned_data.get('email')
    
    def save(self, commit=True):
        """Save profile but don't update email."""
        instance = super().save(commit=False)
        # Ensure email is not changed
        if self.instance and self.instance.pk:
            instance.email = self.instance.email
        
        # Explicitly set nullable fields from cleaned_data
        # This ensures they are saved even if they were empty strings
        address_val = self.cleaned_data.get('address', '')
        if address_val:
            instance.address = str(address_val).strip() or None
        else:
            instance.address = None
        
        city_val = self.cleaned_data.get('city', '')
        if city_val:
            instance.city = str(city_val).strip() or None
        else:
            instance.city = None
        
        state_val = self.cleaned_data.get('state', '')
        if state_val:
            instance.state = str(state_val).strip() or None
        else:
            instance.state = None
        
        pincode_val = self.cleaned_data.get('pincode', '')
        if pincode_val:
            instance.pincode = str(pincode_val).strip() or None
        else:
            instance.pincode = None
        
        if commit:
            instance.save(update_fields=['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode'])
        return instance
    
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
        """Validate password confirmation matches and new password is different from current."""
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        # Check password match
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError({
                    'new_password2': "Passwords do not match. Please enter the same password in both fields."
                })
        
        # Check new password is different from current password
        if current_password and new_password1:
            if current_password == new_password1:
                raise forms.ValidationError({
                    'new_password1': "New password must be different from your current password."
                })
        
        return cleaned_data
    
    def save(self):
        """Update user password using Django's password hashing."""
        if self.user:
            self.user.set_password(self.cleaned_data['new_password1'])
            self.user.save()
        return self.user


class ServicerRegisterForm(UserCreationForm):
    """
    Servicer registration form with comprehensive validation:
    - Service center name, owner name, username, email, phone, password, confirm password
    - Email format validation
    - Phone number validation (exactly 10 digits)
    - Password rules: min 8 chars, uppercase, lowercase, number
    - Password confirmation matching
    - Username and email uniqueness
    - Automatically assigns SERVICER role
    """
    
    service_center_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter service center name'
        }),
        error_messages={
            'required': 'Service center name is required.'
        }
    )
    
    owner_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter owner name'
        }),
        error_messages={
            'required': 'Owner name is required.'
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
            'placeholder': 'Enter 10-digit phone number',
            'maxlength': '10'
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
            'service_center_name', 'owner_name',
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
        Save servicer with SERVICER role and hashed password.
        UserCreationForm's save() method handles password hashing automatically.
        """
        # Call parent save with commit=False to get user object
        user = super().save(commit=False)
        
        # Set role to SERVICER for servicer registration
        user.role = 'SERVICER'
        
        # Set first_name and last_name from owner_name and service_center_name
        user.first_name = self.cleaned_data.get('owner_name', '')
        user.last_name = self.cleaned_data.get('service_center_name', '')
        
        # Ensure user is active (required for login)
        user.is_active = True
        
        # Ensure email is set (required field)
        if not user.email:
            user.email = self.cleaned_data.get('email', '')
        
        # Save the user if commit=True
        # Password is already hashed by UserCreationForm's save method
        if commit:
            user.save()
            # Save many-to-many relationships if any
            self.save_m2m()
        
        return user


class ServicerProfileUpdateForm(forms.ModelForm):
    """
    Form for updating servicer profile information.
    Includes personal info fields plus servicer-specific fields:
    - Service Center Name (stored as last_name)
    - Location
    - Work Types
    - Available Time
    Email is non-editable.
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter owner name'
        }),
        error_messages={
            'required': 'Owner name is required.'
        }
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter service center name'
        }),
        error_messages={
            'required': 'Service center name is required.'
        }
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'readonly': True,
            'disabled': True
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
    
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter service center location'
        })
    )
    
    work_types = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter work types (comma-separated)'
        }),
        help_text='Enter types of work you can do, separated by commas'
    )
    
    available_time = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 9:00 AM - 6:00 PM'
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'state', 'pincode',
            'location', 'work_types', 'available_time'
        ]
    
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
            self.fields['location'].initial = self.instance.location or ''
            self.fields['work_types'].initial = self.instance.work_types or ''
            self.fields['available_time'].initial = self.instance.available_time or '9:00 AM - 6:00 PM'
    
    def clean_email(self):
        """Email is non-editable, return existing email."""
        if self.instance and self.instance.pk:
            return self.instance.email
        return self.cleaned_data.get('email')
    
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
    
    def save(self, commit=True):
        """Save profile but don't update email."""
        instance = super().save(commit=False)
        # Ensure email is not changed
        if self.instance and self.instance.pk:
            instance.email = self.instance.email
        
        # Explicitly set nullable fields from cleaned_data
        # This ensures they are saved even if they were empty strings
        address_val = self.cleaned_data.get('address', '')
        if address_val:
            instance.address = str(address_val).strip() or None
        else:
            instance.address = None
        
        city_val = self.cleaned_data.get('city', '')
        if city_val:
            instance.city = str(city_val).strip() or None
        else:
            instance.city = None
        
        state_val = self.cleaned_data.get('state', '')
        if state_val:
            instance.state = str(state_val).strip() or None
        else:
            instance.state = None
        
        pincode_val = self.cleaned_data.get('pincode', '')
        if pincode_val:
            instance.pincode = str(pincode_val).strip() or None
        else:
            instance.pincode = None
        
        location_val = self.cleaned_data.get('location', '')
        if location_val:
            instance.location = str(location_val).strip() or None
        else:
            instance.location = None
        
        work_types_val = self.cleaned_data.get('work_types', '')
        if work_types_val:
            instance.work_types = str(work_types_val).strip() or None
        else:
            instance.work_types = None
        
        available_time_val = self.cleaned_data.get('available_time', '')
        if available_time_val:
            instance.available_time = str(available_time_val).strip() or None
        else:
            instance.available_time = None
        
        if commit:
            instance.save(update_fields=['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'location', 'work_types', 'available_time'])
        return instance


class RejectBookingForm(forms.Form):
    """Form for rejecting a booking with a reason."""
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter reason for rejecting this service request...',
        }),
        error_messages={
            'required': 'Please provide a reason for rejecting the request.'
        }
    )


class AcceptBookingForm(forms.Form):
    """Form for accepting a booking with pickup choice."""
    pickup_choice = forms.ChoiceField(
        choices=[
            ('pickup', 'Servicer will pickup vehicle'),
            ('user_brings', 'User will bring vehicle'),
        ],
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        error_messages={
            'required': 'Please select how the vehicle will be delivered.'
        }
    )


class DiagnosisForm(forms.ModelForm):
    """
    Form for creating diagnosis.
    
    Fields:
    - report: Problem description (required)
    - work_items: List of work items (required)
    - estimated_cost: Estimated cost (optional)
    - estimated_completion_time: Estimated completion date/time (optional)
    """
    work_items = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter work items, one per line or comma-separated',
        }),
        help_text='Enter each work item on a new line or separated by commas',
        error_messages={
            'required': 'Please provide at least one work item.'
        }
    )
    
    estimated_cost = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text='Optional: Enter estimated cost in ₹'
    )
    
    estimated_completion_time = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 2-3 days or Dec 25, 2024'
        }),
        help_text='Optional: Enter estimated completion time or date'
    )
    
    class Meta:
        model = Diagnosis
        fields = ['report', 'work_items', 'estimated_cost', 'estimated_completion_time']
        widgets = {
            'report': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Enter problem description and diagnosis details...',
            }),
        }
        labels = {
            'report': 'Problem Description',
        }
        help_texts = {
            'report': 'Describe the problems found during vehicle examination',
        }
    
    def clean_work_items(self):
        """Clean and format work items."""
        work_items = self.cleaned_data.get('work_items', '')
        if not work_items or not work_items.strip():
            raise forms.ValidationError("Please provide at least one work item.")
        return work_items
    
    def clean_report(self):
        """Validate report is not empty."""
        report = self.cleaned_data.get('report', '')
        if not report or not report.strip():
            raise forms.ValidationError("Problem description is required.")
        return report


class ProgressUpdateForm(forms.ModelForm):
    """
    Form for adding work progress updates.
    
    Fields:
    - title: Short summary of the progress update (required)
    - description: Detailed work update (required)
    
    Note: status is automatically set to "In Progress" in the view.
    """
    class Meta:
        model = WorkProgress
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Engine repair started, Oil change completed',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Enter detailed progress update...',
            }),
        }
        labels = {
            'title': 'Progress Title',
            'description': 'Progress Description',
        }
        help_texts = {
            'title': 'A short summary of what work has been done',
            'description': 'Detailed description of the progress made',
        }
    
    def clean_title(self):
        """Validate title is not empty."""
        title = self.cleaned_data.get('title', '')
        if not title or not title.strip():
            raise forms.ValidationError("Progress title is required.")
        return title.strip()
    
    def clean_description(self):
        """Validate description is not empty."""
        description = self.cleaned_data.get('description', '')
        if not description or not description.strip():
            raise forms.ValidationError("Progress description is required.")
        return description.strip()


class CompleteWorkForm(forms.Form):
    """
    Form for marking work as completed and requesting payment.
    
    Fields:
    - completion_notes: Optional notes about the completion (optional)
    - final_amount: Final payment amount (required)
    
    Note: Payment is automatically requested when work is marked as completed.
    """
    completion_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter completion notes (optional)...',
        }),
        help_text='Optional: Add any notes about the completed work'
    )
    final_amount = forms.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text='Enter the final payment amount in ₹',
        label='Final Payment Amount (₹)',
        error_messages={
            'required': 'Please enter the final amount.'
        }
    )
    
    def clean_final_amount(self):
        """Validate final amount is positive."""
        final_amount = self.cleaned_data.get('final_amount')
        if final_amount is not None and final_amount <= 0:
            raise forms.ValidationError("Final amount must be greater than zero.")
        return final_amount


class FeedbackForm(forms.ModelForm):
    """
    Form for submitting feedback.
    
    Fields:
    - rating: Required, 1-5 stars
    - message: Required, feedback text
    """
    rating = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),  # Will be set via JavaScript star clicks
        help_text='Rating from 1 to 5 stars'
    )
    
    class Meta:
        model = Feedback
        fields = ['rating', 'message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter your feedback message...',
            }),
        }
        labels = {
            'message': 'Feedback Message',
        }
        help_texts = {
            'message': 'Please share your experience with this service',
        }
    
    def clean_rating(self):
        """Validate rating is between 1 and 5."""
        rating = self.cleaned_data.get('rating')
        if rating is None:
            raise forms.ValidationError("Please select a rating.")
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Rating must be between 1 and 5 stars.")
        return rating
    
    def clean_message(self):
        """Validate message is not empty."""
        message = self.cleaned_data.get('message', '')
        if not message or not message.strip():
            raise forms.ValidationError("Feedback message is required.")
        return message.strip()