"""
Test utilities for creating test data and managing test clients.

This module provides reusable helper functions for:
- Creating users with different roles
- Creating servicers
- Creating bookings
- Logging in test clients

All functions follow best practices:
- No hardcoded IDs
- No magic strings (use constants)
- Use factories/helpers where possible
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

from accounts.models import User, Servicer, Booking, Diagnosis, WorkProgress, Feedback

# Constants for role choices (avoid magic strings)
ROLE_USER = 'USER'
ROLE_SERVICER = 'SERVICER'
ROLE_ADMIN = 'ADMIN'

# Constants for booking status choices
STATUS_REQUESTED = 'Requested'
STATUS_ACCEPTED = 'Accepted'
STATUS_PENDING = 'Pending'
STATUS_ONGOING = 'Ongoing'
STATUS_COMPLETED = 'Completed'
STATUS_REJECTED = 'Rejected'

# Constants for payment status
PAYMENT_STATUS_PENDING = 'Pending'
PAYMENT_STATUS_PAID = 'Paid'

# Constants for work progress status
PROGRESS_STATUS_PENDING = 'Pending'
PROGRESS_STATUS_IN_PROGRESS = 'In Progress'
PROGRESS_STATUS_COMPLETED = 'Completed'

# Constants for servicer status
SERVICER_STATUS_AVAILABLE = 'Available'
SERVICER_STATUS_BUSY = 'Busy'
SERVICER_STATUS_UNAVAILABLE = 'Unavailable'


def create_user(
    username=None,
    email=None,
    phone=None,
    password='TestPass123',
    role=ROLE_USER,
    first_name=None,
    last_name=None,
    **kwargs
):
    """
    Create a test user with the specified parameters.
    
    Args:
        username: Username for the user (auto-generated if not provided)
        email: Email address (auto-generated if not provided)
        phone: Phone number (10 digits, auto-generated if not provided)
        password: Password (default: 'TestPass123')
        role: User role - 'USER', 'SERVICER', or 'ADMIN' (default: 'USER')
        first_name: First name (optional)
        last_name: Last name (optional)
        **kwargs: Additional fields (address, city, state, pincode, location, work_types, available_time)
    
    Returns:
        User instance
    
    Example:
        user = create_user(username='testuser', role=ROLE_USER)
        servicer_user = create_user(username='servicer1', role=ROLE_SERVICER, location='City A')
    """
    User = get_user_model()
    
    # Generate unique username if not provided
    if username is None:
        username = f'testuser_{timezone.now().timestamp()}'
    
    # Generate unique email if not provided
    if email is None:
        email = f'{username}@example.com'
    
    # Generate phone number if not provided (10 digits)
    if phone is None:
        phone = f'{int(timezone.now().timestamp()) % 10000000000:010d}'
    
    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        phone=phone,
        password=password,
        role=role,
        first_name=first_name or '',
        last_name=last_name or '',
        **kwargs
    )
    
    return user


def create_servicer(
    name=None,
    work_type=None,
    location=None,
    phone=None,
    email=None,
    rating=4.5,
    available_time='9:00 AM - 6:00 PM',
    status=None,
    profile_image='',
    **kwargs
):
    """
    Create a test servicer (Servicer model instance).
    
    Args:
        name: Service center name (auto-generated if not provided)
        work_type: Type of work servicer does (default: 'General Service')
        location: Service center location (auto-generated if not provided)
        phone: Phone number (10 digits, auto-generated if not provided)
        email: Email address (auto-generated if not provided)
        rating: Average rating (default: 4.5)
        available_time: Available working hours (default: '9:00 AM - 6:00 PM')
        status: Servicer status - 'Available', 'Busy', or 'Unavailable' (default: 'Available')
        profile_image: Profile image URL (optional)
        **kwargs: Additional fields
    
    Returns:
        Servicer instance
    
    Example:
        servicer = create_servicer(name='Auto Service Center', location='City A')
    """
    # Generate unique name if not provided
    if name is None:
        name = f'Service Center {timezone.now().timestamp()}'
    
    # Set default work_type if not provided
    if work_type is None:
        work_type = 'General Service'
    
    # Generate location if not provided
    if location is None:
        location = f'Location {timezone.now().timestamp()}'
    
    # Generate phone if not provided (10 digits)
    if phone is None:
        phone = f'{int(timezone.now().timestamp()) % 10000000000:010d}'
    
    # Generate email if not provided
    if email is None:
        email = f'servicer_{timezone.now().timestamp()}@example.com'
    
    # Set default status if not provided
    if status is None:
        status = SERVICER_STATUS_AVAILABLE
    
    servicer = Servicer.objects.create(
        name=name,
        work_type=work_type,
        location=location,
        phone=phone,
        email=email,
        rating=rating,
        available_time=available_time,
        status=status,
        profile_image=profile_image,
        **kwargs
    )
    
    return servicer


def create_booking(
    user=None,
    servicer=None,
    vehicle_make='Toyota',
    vehicle_model='Camry',
    owner_name=None,
    fuel_type='Petrol',
    year=2020,
    vehicle_number=None,
    work_type='General Service',
    preferred_date=None,
    complaints='Engine noise',
    status=STATUS_REQUESTED,
    **kwargs
):
    """
    Create a test booking.
    
    Args:
        user: User instance (creates one if not provided)
        servicer: Servicer instance (creates one if not provided)
        vehicle_make: Vehicle make (default: 'Toyota')
        vehicle_model: Vehicle model (default: 'Camry')
        owner_name: Owner name (uses user's full name if not provided)
        fuel_type: Fuel type (default: 'Petrol')
        year: Vehicle year (default: 2020)
        vehicle_number: Vehicle registration number (auto-generated if not provided)
        work_type: Type of work requested (default: 'General Service')
        preferred_date: Preferred service date (default: tomorrow)
        complaints: Service complaints/description (default: 'Engine noise')
        status: Booking status (default: 'Requested')
        **kwargs: Additional fields (rejection_reason, pickup_choice, payment_requested, 
                 final_amount, completion_notes, payment_status, payment_date, vehicle_photo)
    
    Returns:
        Booking instance
    
    Example:
        booking = create_booking(user=user, servicer=servicer, status=STATUS_PENDING)
    """
    # Create user if not provided
    if user is None:
        user = create_user()
    
    # Create servicer if not provided
    if servicer is None:
        servicer = create_servicer()
    
    # Use user's full name if owner_name not provided
    if owner_name is None:
        owner_name = f'{user.first_name} {user.last_name}'.strip() or user.username
    
    # Generate vehicle number if not provided
    if vehicle_number is None:
        vehicle_number = f'TEST{int(timezone.now().timestamp()) % 10000:04d}'
    
    # Set preferred_date to tomorrow if not provided
    if preferred_date is None:
        preferred_date = date.today() + timedelta(days=1)
    
    booking = Booking.objects.create(
        user=user,
        servicer=servicer,
        vehicle_make=vehicle_make,
        vehicle_model=vehicle_model,
        owner_name=owner_name,
        fuel_type=fuel_type,
        year=year,
        vehicle_number=vehicle_number,
        work_type=work_type,
        preferred_date=preferred_date,
        complaints=complaints,
        status=status,
        **kwargs
    )
    
    return booking


def create_diagnosis(
    booking=None,
    report='Diagnosis report',
    work_items='Oil change, Filter replacement',
    estimated_cost=5000.00,
    estimated_completion_time='2 days',
    user_approved=False,
    user_rejected=False
):
    """
    Create a test diagnosis for a booking.
    
    Args:
        booking: Booking instance (creates one if not provided)
        report: Diagnosis report text (default: 'Diagnosis report')
        work_items: Comma-separated work items (default: 'Oil change, Filter replacement')
        estimated_cost: Estimated cost (default: 5000.00)
        estimated_completion_time: Estimated completion time (default: '2 days')
        user_approved: Whether user approved diagnosis (default: False)
        user_rejected: Whether user rejected diagnosis (default: False)
    
    Returns:
        Diagnosis instance
    
    Example:
        diagnosis = create_diagnosis(booking=booking, user_approved=True)
    """
    # Create booking if not provided
    if booking is None:
        booking = create_booking()
    
    diagnosis = Diagnosis.objects.create(
        booking=booking,
        report=report,
        work_items=work_items,
        estimated_cost=estimated_cost,
        estimated_completion_time=estimated_completion_time,
        user_approved=user_approved,
        user_rejected=user_rejected
    )
    
    return diagnosis


def create_work_progress(
    booking=None,
    title='Work Update',
    description='Progress update description',
    status=PROGRESS_STATUS_IN_PROGRESS
):
    """
    Create a test work progress entry.
    
    Args:
        booking: Booking instance (creates one if not provided)
        title: Progress title (default: 'Work Update')
        description: Progress description (default: 'Progress update description')
        status: Progress status - 'Pending', 'In Progress', or 'Completed' (default: 'In Progress')
    
    Returns:
        WorkProgress instance
    
    Example:
        progress = create_work_progress(booking=booking, status=PROGRESS_STATUS_COMPLETED)
    """
    # Create booking if not provided
    if booking is None:
        booking = create_booking()
    
    progress = WorkProgress.objects.create(
        booking=booking,
        title=title,
        description=description,
        status=status
    )
    
    return progress


def create_feedback(
    user=None,
    booking=None,
    servicer=None,
    rating=5,
    message='Great service!'
):
    """
    Create a test feedback entry.
    
    Args:
        user: User instance (creates one if not provided)
        booking: Booking instance (creates one if not provided)
        servicer: Servicer instance (uses booking's servicer if not provided)
        rating: Rating from 1 to 5 (default: 5)
        message: Feedback message (default: 'Great service!')
    
    Returns:
        Feedback instance
    
    Example:
        feedback = create_feedback(user=user, booking=booking, rating=4)
    """
    # Create user if not provided
    if user is None:
        user = create_user()
    
    # Create booking if not provided
    if booking is None:
        booking = create_booking(user=user)
    
    # Use booking's servicer if servicer not provided
    if servicer is None:
        servicer = booking.servicer
    
    feedback = Feedback.objects.create(
        user=user,
        booking=booking,
        servicer=servicer,
        rating=rating,
        message=message
    )
    
    return feedback


def login_user(client, user=None, username=None, password='TestPass123'):
    """
    Log in a test client with the specified user.
    
    Args:
        client: Django TestClient instance
        user: User instance to log in (creates one if not provided)
        username: Username to log in with (uses user.username if user provided)
        password: Password to log in with (default: 'TestPass123')
    
    Returns:
        User instance that was logged in
    
    Example:
        client = Client()
        user = login_user(client, username='testuser')
    """
    # Create user if not provided
    if user is None:
        if username is None:
            username = f'testuser_{timezone.now().timestamp()}'
        user = create_user(username=username, password=password)
    
    # Log in the client
    client.login(username=user.username, password=password)
    
    return user


def login_as_role(client, role, username=None, password='TestPass123'):
    """
    Log in a test client as a user with the specified role.
    
    Args:
        client: Django TestClient instance
        role: Role to log in as - 'USER', 'SERVICER', or 'ADMIN'
        username: Username (auto-generated if not provided)
        password: Password (default: 'TestPass123')
    
    Returns:
        User instance that was logged in
    
    Example:
        client = Client()
        servicer = login_as_role(client, ROLE_SERVICER)
        admin = login_as_role(client, ROLE_ADMIN)
    """
    if username is None:
        username = f'{role.lower()}_{timezone.now().timestamp()}'
    
    user = create_user(username=username, password=password, role=role)
    client.login(username=username, password=password)
    
    return user


class BaseTestCase(TestCase):
    """
    Base test case class with common setup and helper methods.
    
    Extend this class for test cases that need common setup or helper methods.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
    
    def create_test_user(self, **kwargs):
        """Create a test user (convenience method)."""
        return create_user(**kwargs)
    
    def create_test_servicer(self, **kwargs):
        """Create a test servicer (convenience method)."""
        return create_servicer(**kwargs)
    
    def create_test_booking(self, **kwargs):
        """Create a test booking (convenience method)."""
        return create_booking(**kwargs)
    
    def login_test_user(self, **kwargs):
        """Log in a test user (convenience method)."""
        return login_user(self.client, **kwargs)
