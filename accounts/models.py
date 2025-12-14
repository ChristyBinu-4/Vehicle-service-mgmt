from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('servicer', 'Servicer'),
        ('admin', 'Admin'),
    )
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username

class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Feedback"

class WorkProgress(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    )
    
    booking = models.ForeignKey(
        "Booking",
        on_delete=models.CASCADE,
        related_name="progress",
        null=True,
        blank=True
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
        ("Requested", "Requested"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Ongoing", "Ongoing"),
        ("Completed", "Completed"),
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

    def __str__(self):
        return f"{self.vehicle_number} - {self.servicer.name}"


class Diagnosis(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="diagnosis"
    )
    report = models.TextField()
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnosis for Booking #{self.booking.id}"
