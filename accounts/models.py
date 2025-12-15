from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings


class User(AbstractUser):
    """
    Custom User model extending AbstractUser.
    Stores user role (USER, SERVICER, ADMIN), phone number (10 digits),
    and ensures email and username uniqueness.
    """
    ROLE_CHOICES = (
        ('USER', 'User'),
        ('SERVICER', 'Servicer'),
        ('ADMIN', 'Admin'),
    )
    
    # Email field with uniqueness constraint
    email = models.EmailField(unique=True, verbose_name='email address')
    
    # Phone number field with validation for exactly 10 digits
    phone_validator = RegexValidator(
        regex=r'^\d{10}$',
        message='Phone number must be exactly 10 digits.'
    )
    phone = models.CharField(
        max_length=10,
        validators=[phone_validator],
        verbose_name='phone number',
        help_text='Phone number must be exactly 10 digits'
    )
    
    # Role field with choices: USER, SERVICER, ADMIN
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='USER',
        verbose_name='user role'
    )
    
    # Address fields (nullable, optional)
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='address',
        help_text='Street address'
    )
    
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='city'
    )
    
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='state'
    )
    
    pincode = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name='pincode'
    )
    
    # Servicer-specific fields (nullable, optional)
    location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='location',
        help_text='Service center location'
    )
    
    work_types = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='work types',
        help_text='Types of work the servicer can do (comma-separated)'
    )
    
    available_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='available time',
        help_text='Available working hours',
        default='9:00 AM - 6:00 PM'
    )

    def __str__(self):
        return self.username

class Feedback(models.Model):
    """
    Feedback model for user reviews.
    Linked to user, booking, and servicer.
    Rating affects servicer profile (aggregated).
    """
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedbacks')
    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='feedback',
        blank=True,
        null=True,
        help_text="One feedback per booking"
    )
    servicer = models.ForeignKey(
        'Servicer',
        on_delete=models.CASCADE,
        related_name='feedbacks',
        blank=True,
        null=True,
        help_text="Servicer who completed the service"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        blank=True,
        null=True,
        help_text="Rating from 1 to 5 stars"
    )
    message = models.TextField(help_text="Feedback message")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"{self.user.username} - {self.rating} stars - Booking #{self.booking.id}"

class WorkProgress(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    )
    
    booking = models.ForeignKey(
        "Booking",
        on_delete=models.CASCADE,
        related_name="progress"
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking.id} - {self.title} ({self.status})"

class Servicer(models.Model):
    STATUS_CHOICES = (
        ("Available", "Available"),
        ("Busy", "Busy"),
        ("Unavailable", "Unavailable"),
    )

    name = models.CharField(max_length=100)
    work_type = models.CharField(max_length=200)
    location = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.5)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    available_time = models.CharField(
        max_length=100,
        default="9:00 AM - 6:00 PM"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    profile_image = models.URLField(blank=True)

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = (
        ("Requested", "Service Requested"),
        ("Accepted", "Accepted"),
        ("Pending", "Pending"),
        ("Ongoing", "Ongoing"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    servicer = models.ForeignKey(Servicer, on_delete=models.CASCADE)

    vehicle_make = models.CharField(max_length=100)
    vehicle_model = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    fuel_type = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    vehicle_number = models.CharField(max_length=20)
    vehicle_photo = models.ImageField(upload_to="vehicles/", blank=True, null=True)

    work_type = models.CharField(max_length=100)
    preferred_date = models.DateField()

    complaints = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Requested")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional fields for work lifecycle
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejecting the service request")
    pickup_choice = models.CharField(
        max_length=20,
        choices=[("pickup", "Servicer will pickup"), ("user_brings", "User will bring vehicle")],
        blank=True,
        null=True
    )
    payment_requested = models.BooleanField(default=False)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    completion_notes = models.TextField(blank=True, null=True)
    
    # Payment status tracking
    PAYMENT_STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Paid", "Paid"),
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Payment status: Pending or Paid"
    )
    payment_date = models.DateTimeField(blank=True, null=True, help_text="Date and time when payment was completed")

    def __str__(self):
        return f"{self.vehicle_number} - {self.servicer.name}"


class Diagnosis(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="diagnosis"
    )
    report = models.TextField()
    work_items = models.TextField(blank=True, null=True, help_text="Comma-separated list of work items")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estimated_completion_time = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user_approved = models.BooleanField(default=False)
    user_rejected = models.BooleanField(default=False)

    def __str__(self):
        return f"Diagnosis for Booking #{self.booking.id}"
    
    def get_work_items_list(self):
        """Return work items as a list."""
        if self.work_items:
            return [item.strip() for item in self.work_items.split(",") if item.strip()]
        return []


class SystemSettings(models.Model):
    """
    System-wide settings model (singleton pattern).
    Stores background images for User and Servicer interfaces.
    Only ONE instance should exist.
    """
    user_background_image = models.ImageField(
        upload_to='system/user_backgrounds/',
        blank=True,
        null=True,
        help_text="Background image for User interface"
    )
    servicer_background_image = models.ImageField(
        upload_to='system/servicer_backgrounds/',
        blank=True,
        null=True,
        help_text="Background image for Servicer interface"
    )
    landing_hero_image = models.ImageField(
        upload_to='system/landing/',
        blank=True,
        null=True,
        help_text="Hero image for landing page (main banner image)"
    )
    landing_service_image = models.ImageField(
        upload_to='system/landing/',
        blank=True,
        null=True,
        help_text="Service image for landing page (Why Choose Us section)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    @classmethod
    def get_settings(cls):
        """
        Get or create the singleton SystemSettings instance.
        Ensures only ONE row exists.
        """
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
