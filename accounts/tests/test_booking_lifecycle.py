"""
Test the complete booking lifecycle state machine.

Tests verify:
1. User can create booking
2. Booking starts as "Requested"
3. Servicer accepts → status becomes "Pending"
4. User cannot approve diagnosis before diagnosis exists
5. Diagnosis submission does NOT change status
6. User approval → status becomes "Ongoing"
7. Servicer completes → status becomes "Completed"
8. Invalid state transitions are rejected

All tests follow @vms_requirements.txt as the single source of truth.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.tests.test_utils import (
    create_user, create_servicer, create_booking, create_diagnosis, create_work_progress,
    ROLE_USER, ROLE_SERVICER,
    STATUS_REQUESTED, STATUS_PENDING, STATUS_ONGOING, STATUS_COMPLETED,
    BaseTestCase
)
from accounts.models import Booking, Diagnosis, WorkProgress, Servicer

User = get_user_model()


class BookingCreationTests(TestCase):
    """Test booking creation and initial state."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_user_can_create_booking(self):
        """
        Test that user can create a booking.
        Expected: Booking is created with status "Requested".
        """
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Create booking via the booking_confirm view
        # First, set session data (simulating book_service view)
        session = self.client.session
        session['booking_data'] = {
            'servicer_id': self.servicer.id,
            'vehicle_make': 'Toyota',
            'vehicle_model': 'Camry',
            'owner_name': 'John Doe',
            'fuel_type': 'Petrol',
            'year': 2020,
            'vehicle_number': 'ABC123',
            'work_type': 'General Service',
            'preferred_date': '2024-12-25',
            'complaints': 'Engine noise'
        }
        session.save()
        
        # Submit booking confirmation
        response = self.client.post(reverse('booking_confirm'))
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Verify booking was created
        booking = Booking.objects.filter(user=self.user, servicer=self.servicer).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.vehicle_make, 'Toyota')
        self.assertEqual(booking.vehicle_model, 'Camry')
    
    def test_booking_starts_as_requested(self):
        """
        Test that booking starts with status "Requested".
        Expected: New booking has status="Requested" (default).
        """
        booking = create_booking(user=self.user, servicer=self.servicer)
        
        # Verify initial status
        self.assertEqual(booking.status, STATUS_REQUESTED)
        self.assertEqual(booking.status, 'Requested')
        
        # Verify booking is linked correctly
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.servicer, self.servicer)


class BookingStateTransitionTests(BaseTestCase):
    """Test valid state transitions in booking lifecycle."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
        self.booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_REQUESTED
        )
    
    def test_servicer_accepts_booking_status_becomes_pending(self):
        """
        Test that servicer accepting booking moves status to "Pending".
        Expected: Status changes from "Requested" to "Pending".
        """
        # Verify initial status
        self.assertEqual(self.booking.status, STATUS_REQUESTED)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Accept booking
        response = self.client.post(
            reverse('accept_booking', args=[self.booking.id]),
            {'pickup_choice': 'pickup'}
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        self.booking.refresh_from_db()
        
        # Verify status changed to Pending
        self.assertEqual(self.booking.status, STATUS_PENDING)
        self.assertEqual(self.booking.pickup_choice, 'pickup')
        
        # Verify WorkProgress entry was created
        progress = WorkProgress.objects.filter(booking=self.booking).first()
        self.assertIsNotNone(progress)
        self.assertIn('Request Accepted', progress.title)
    
    def test_diagnosis_submission_does_not_change_status(self):
        """
        Test that diagnosis submission does NOT change booking status.
        Expected: Status remains "Pending" after diagnosis is created.
        """
        # Set booking to Pending (after acceptance)
        self.booking.status = STATUS_PENDING
        self.booking.save()
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Create diagnosis
        response = self.client.post(
            reverse('create_diagnosis', args=[self.booking.id]),
            {
                'report': 'Engine needs oil change and filter replacement',
                'work_items': 'Oil change, Filter replacement',
                'estimated_cost': '5000.00',
                'estimated_completion_time': '2 days'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        self.booking.refresh_from_db()
        
        # Verify status is still Pending (NOT changed)
        self.assertEqual(self.booking.status, STATUS_PENDING)
        
        # Verify diagnosis was created
        self.assertTrue(hasattr(self.booking, 'diagnosis'))
        diagnosis = self.booking.diagnosis
        self.assertEqual(diagnosis.report, 'Engine needs oil change and filter replacement')
        self.assertFalse(diagnosis.user_approved)  # Not yet approved
    
    def test_user_cannot_approve_diagnosis_before_diagnosis_exists(self):
        """
        Test that user cannot approve diagnosis before diagnosis exists.
        Expected: Approval fails with error, status remains unchanged.
        """
        # Set booking to Pending (after acceptance)
        self.booking.status = STATUS_PENDING
        self.booking.save()
        
        # Verify no diagnosis exists
        self.assertFalse(hasattr(self.booking, 'diagnosis'))
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to approve diagnosis (should fail)
        response = self.client.post(
            reverse('approve_diagnosis', args=[self.booking.id])
        )
        
        # Should redirect back to booking detail with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        self.booking.refresh_from_db()
        
        # Verify status is still Pending (NOT changed to Ongoing)
        self.assertEqual(self.booking.status, STATUS_PENDING)
    
    def test_user_approval_moves_status_to_ongoing(self):
        """
        Test that user approving diagnosis moves status to "Ongoing".
        Expected: Status changes from "Pending" to "Ongoing" after approval.
        """
        # Set booking to Pending and create diagnosis
        self.booking.status = STATUS_PENDING
        self.booking.save()
        
        diagnosis = create_diagnosis(
            booking=self.booking,
            report='Diagnosis report',
            user_approved=False
        )
        
        # Verify initial state
        self.assertEqual(self.booking.status, STATUS_PENDING)
        self.assertFalse(diagnosis.user_approved)
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Approve diagnosis
        response = self.client.post(
            reverse('approve_diagnosis', args=[self.booking.id])
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking and diagnosis from database
        self.booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status changed to Ongoing
        self.assertEqual(self.booking.status, STATUS_ONGOING)
        
        # Verify diagnosis is approved
        self.assertTrue(diagnosis.user_approved)
    
    def test_servicer_completes_work_status_becomes_completed(self):
        """
        Test that servicer completing work moves status to "Completed".
        Expected: Status changes from "Ongoing" to "Completed".
        """
        # Set booking to Ongoing with approved diagnosis
        self.booking.status = STATUS_ONGOING
        self.booking.save()
        
        diagnosis = create_diagnosis(
            booking=self.booking,
            user_approved=True
        )
        
        # Create at least one WorkProgress entry (required for completion)
        create_work_progress(
            booking=self.booking,
            title='Work started',
            description='Initial work progress',
            status='In Progress'
        )
        
        # Verify initial state
        self.assertEqual(self.booking.status, STATUS_ONGOING)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Mark work as completed
        response = self.client.post(
            reverse('mark_work_completed', args=[self.booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'Work completed successfully'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        self.booking.refresh_from_db()
        
        # Verify status changed to Completed
        self.assertEqual(self.booking.status, STATUS_COMPLETED)
        
        # Verify payment fields are set
        self.assertTrue(self.booking.payment_requested)
        self.assertEqual(self.booking.payment_status, 'Pending')
        self.assertEqual(str(self.booking.final_amount), '5500.00')
        self.assertEqual(self.booking.completion_notes, 'Work completed successfully')
        
        # Verify completion WorkProgress entry was created
        completion_progress = WorkProgress.objects.filter(
            booking=self.booking,
            title='Service Completed'
        ).first()
        self.assertIsNotNone(completion_progress)


class InvalidStateTransitionTests(BaseTestCase):
    """Test that invalid state transitions are rejected."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_cannot_accept_non_requested_booking(self):
        """
        Test that servicer cannot accept booking that is not in "Requested" status.
        Expected: Acceptance fails, status remains unchanged.
        """
        # Create booking in Pending status
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Try to accept booking (should fail)
        response = self.client.post(
            reverse('accept_booking', args=[booking.id]),
            {'pickup_choice': 'pickup'}
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify status is still Pending (NOT changed)
        self.assertEqual(booking.status, STATUS_PENDING)
    
    def test_cannot_create_diagnosis_for_non_pending_booking(self):
        """
        Test that servicer cannot create diagnosis for booking not in "Pending" status.
        Expected: Diagnosis creation fails, status remains unchanged.
        """
        # Create booking in Requested status (not yet accepted)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_REQUESTED
        )
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Try to create diagnosis (should fail)
        response = self.client.post(
            reverse('create_diagnosis', args=[booking.id]),
            {
                'report': 'Diagnosis report',
                'work_items': 'Work items',
                'estimated_cost': '5000.00'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Verify diagnosis was NOT created
        self.assertFalse(hasattr(booking, 'diagnosis'))
        
        # Verify status is still Requested
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_REQUESTED)
    
    def test_cannot_approve_diagnosis_for_non_pending_booking(self):
        """
        Test that user cannot approve diagnosis for booking not in "Pending" status.
        Expected: Approval fails, status remains unchanged.
        """
        # Create booking in Ongoing status (already approved)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=False
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to approve diagnosis (should fail)
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking and diagnosis from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status is still Ongoing (NOT changed)
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Verify diagnosis is still not approved
        self.assertFalse(diagnosis.user_approved)
    
    def test_cannot_complete_non_ongoing_booking(self):
        """
        Test that servicer cannot complete booking that is not in "Ongoing" status.
        Expected: Completion fails, status remains unchanged.
        """
        # Create booking in Pending status (not yet approved)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Try to mark as completed (should fail)
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'Work done'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify status is still Pending (NOT changed to Completed)
        self.assertEqual(booking.status, STATUS_PENDING)
    
    def test_cannot_complete_booking_without_progress_updates(self):
        """
        Test that servicer cannot complete booking without at least one WorkProgress entry.
        Expected: Completion fails, status remains unchanged.
        """
        # Create booking in Ongoing status with approved diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        create_diagnosis(
            booking=booking,
            user_approved=True
        )
        
        # Verify no WorkProgress entries exist
        self.assertEqual(WorkProgress.objects.filter(booking=booking).count(), 0)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Try to mark as completed (should fail - no progress updates)
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'Work done'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify status is still Ongoing (NOT changed to Completed)
        self.assertEqual(booking.status, STATUS_ONGOING)


class CompleteLifecycleFlowTests(BaseTestCase):
    """Test the complete booking lifecycle from creation to completion."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_complete_booking_lifecycle(self):
        """
        Test the complete booking lifecycle flow:
        Requested → Pending → Ongoing → Completed
        
        Expected: All state transitions occur correctly in sequence.
        """
        # Step 1: Create booking (starts as Requested)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_REQUESTED
        )
        self.assertEqual(booking.status, STATUS_REQUESTED)
        
        # Step 2: Servicer accepts → Pending
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        response = self.client.post(
            reverse('accept_booking', args=[booking.id]),
            {'pickup_choice': 'pickup'}
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_PENDING)
        
        # Step 3: Servicer creates diagnosis (status remains Pending)
        response = self.client.post(
            reverse('create_diagnosis', args=[booking.id]),
            {
                'report': 'Diagnosis report',
                'work_items': 'Oil change, Filter replacement',
                'estimated_cost': '5000.00',
                'estimated_completion_time': '2 days'
            }
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_PENDING)  # Still Pending
        self.assertTrue(hasattr(booking, 'diagnosis'))
        
        # Step 4: User approves diagnosis → Ongoing
        self.client.logout()
        self.client.login(username=self.user.username, password='TestPass123')
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_ONGOING)
        self.assertTrue(booking.diagnosis.user_approved)
        
        # Step 5: Servicer adds progress update
        self.client.logout()
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        response = self.client.post(
            reverse('add_progress_update', args=[booking.id]),
            {
                'title': 'Work in progress',
                'description': 'Completed oil change, working on filter'
            }
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_ONGOING)  # Still Ongoing
        
        # Step 6: Servicer completes work → Completed
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'All work completed successfully'
            }
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_COMPLETED)
        self.assertTrue(booking.payment_requested)
        self.assertEqual(booking.payment_status, 'Pending')
        self.assertEqual(str(booking.final_amount), '5500.00')
