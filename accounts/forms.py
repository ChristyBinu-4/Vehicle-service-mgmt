from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, Feedback, Diagnosis, WorkProgress, Booking


class UserRegisterForm(UserCreationForm):
    """
    Form for user registration.
    Extends UserCreationForm to include first_name, last_name, email, and phone.
    Automatically sets role to USER.
    """
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'autocomplete': 'email'})
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'maxlength': '10'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone',
            'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit() or len(phone) != 10:
            raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def save(self, commit=True):
        """
        Save user with USER role and hashed password.
        UserCreationForm's save() method handles password hashing automatically.
        Explicitly saves all personal information fields to ensure persistence.
        """
        # Call parent save with commit=False to get user object
        # This will create the user instance and set the hashed password
        user = super().save(commit=False)
        
        # Set role to USER for user registration
        user.role = 'USER'
        
        # Ensure user is active (required for login)
        user.is_active = True
        
        # Explicitly set all personal information fields from cleaned_data
        # This ensures they are saved to the database
        user.email = self.cleaned_data.get('email', '')
        user.phone = self.cleaned_data.get('phone', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        
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
    Includes all personal information fields including address fields.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Make email read-only for existing users
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] = 'form-control bg-light'
        
        # Make required fields not required to allow keeping old values
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        
        # Add Bootstrap classes
        for field in self.fields:
            if field != 'email':
                self.fields[field].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        """
        Save profile with all personal information fields.
        """
        instance = super().save(commit=False)
        # Ensure email is not changed
        if self.instance and self.instance.pk:
            instance.email = self.instance.email
            # Keep old values if cleared
            if not instance.first_name:
                instance.first_name = self.instance.first_name or ''
            if not instance.last_name:
                instance.last_name = self.instance.last_name or ''
            if not instance.phone:
                instance.phone = self.instance.phone
        
        if commit:
            instance.save()
        return instance
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and (not phone.isdigit() or len(phone) != 10):
            raise ValidationError("Phone number must be exactly 10 digits.")
        return phone


class PasswordChangeForm(forms.Form):
    """
    Custom password change form.
    """
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'}),
        label='Current Password'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label='New Password',
        min_length=8
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label='Confirm New Password'
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError("Your old password was entered incorrectly. Please enter it again.")
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit=True):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class ServicerRegisterForm(UserCreationForm):
    """
    Form for servicer registration.
    Extends UserCreationForm to include service center name, email, and phone.
    Automatically sets role to SERVICER and creates Servicer model instance.
    """
    service_center_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service Center Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'autocomplete': 'email'})
    )
    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'maxlength': '10'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'service_center_name', 'email', 'phone',
            'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit() or len(phone) != 10:
            raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def save(self, commit=True):
        """
        Save servicer with SERVICER role and hashed password.
        Also creates the Servicer model instance linked to the user.
        """
        # Call parent save with commit=False to get user object
        user = super().save(commit=False)
        
        # Set role to SERVICER for servicer registration
        user.role = 'SERVICER'
        
        # Ensure user is active (required for login)
        user.is_active = True
        
        # Set email and phone from cleaned_data
        user.email = self.cleaned_data.get('email', '')
        user.phone = self.cleaned_data.get('phone', '')
        # Set first_name to service_center_name for servicer
        user.first_name = self.cleaned_data.get('service_center_name', '')
        
        if commit:
            user.save()
            self.save_m2m()
            # Create Servicer model instance linked to this user
            from .models import Servicer
            Servicer.objects.create(
                name=self.cleaned_data.get('service_center_name', ''),
                work_type='',
                location='',
                phone=self.cleaned_data.get('phone', ''),
                email=user.email,
                available_time='9:00 AM - 6:00 PM',
                status='Available'
            )
        
        return user


class ServicerProfileUpdateForm(forms.ModelForm):
    """
    Form for updating servicer profile information.
    Includes all personal information fields including address and servicer-specific fields.
    Also updates the linked Servicer model instance.
    """
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
            # Make email read-only for existing users
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] = 'form-control bg-light'
        
        # Make required fields not required to allow keeping old values
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        
        # Add Bootstrap classes
        for field in self.fields:
            if field != 'email':
                self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Pre-populate fields with current user data
        if self.instance and self.instance.pk:
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

    def save(self, commit=True):
        """
        Save servicer profile with all personal information fields.
        Also updates the linked Servicer model instance.
        """
        instance = super().save(commit=False)
        # Ensure email is not changed
        if self.instance and self.instance.pk:
            instance.email = self.instance.email
            # Keep old values if cleared
            if not instance.first_name:
                instance.first_name = self.instance.first_name or ''
            if not instance.last_name:
                instance.last_name = self.instance.last_name or ''
            if not instance.phone:
                instance.phone = self.instance.phone
        
        if commit:
            instance.save()
            
            # Also update the linked Servicer model instance
            try:
                from .models import Servicer
                servicer = Servicer.objects.get(email=instance.email)
                # Update servicer fields from user fields
                servicer.location = instance.location or ''
                servicer.work_type = instance.work_types or ''
                servicer.available_time = instance.available_time or '9:00 AM - 6:00 PM'
                servicer.save()
            except Servicer.DoesNotExist:
                # Servicer instance doesn't exist, skip update
                pass
        
        return instance

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and (not phone.isdigit() or len(phone) != 10):
            raise ValidationError("Phone number must be exactly 10 digits.")
        return phone


class FeedbackForm(forms.ModelForm):
    """
    Form for submitting feedback/rating for a completed booking.
    """
    class Meta:
        model = Feedback
        fields = ['rating', 'message']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your feedback...'})
        }


class AcceptBookingForm(forms.Form):
    """
    Form for accepting a booking request.
    """
    pickup_choice = forms.ChoiceField(
        choices=[("pickup", "Servicer will pickup"), ("user_brings", "User will bring vehicle")],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Vehicle Delivery Method'
    )


class RejectBookingForm(forms.Form):
    """
    Form for rejecting a booking request with a reason.
    """
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide a reason for rejection...'}),
        label='Rejection Reason',
        required=True
    )


class DiagnosisForm(forms.ModelForm):
    """
    Form for creating a diagnosis for a booking.
    """
    class Meta:
        model = Diagnosis
        fields = ['report', 'work_items', 'estimated_cost', 'estimated_completion_time']
        widgets = {
            'report': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Diagnosis report...'}),
            'work_items': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Comma-separated list of work items...'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'estimated_completion_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2-3 days'})
        }


class ProgressUpdateForm(forms.ModelForm):
    """
    Form for adding progress updates to ongoing work.
    """
    class Meta:
        model = WorkProgress
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Progress title...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Progress description...'})
        }


class CompleteWorkForm(forms.Form):
    """
    Form for marking work as completed and requesting payment.
    """
    final_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
        label='Final Amount (₹)'
    )
    completion_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Completion notes (optional)...'}),
        label='Completion Notes'
    )
