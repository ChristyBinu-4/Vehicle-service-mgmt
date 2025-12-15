"""
Test service completion and payment flow.

Tests verify:
1. Servicer cannot complete without progress
2. Completion creates payment request
3. User sees payment
4. User can pay only once
5. Payment marks booking final

All tests follow @vms_requirements.txt as the single source of truth.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.tests.test_utils import (
    create_user, create_servicer, create_booking, create_diagnosis, create_work_progress,
    ROLE_USER, ROLE_SERVICER,
    STATUS_ONGOING, STATUS_COMPLETED,
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    BaseTestCase
)
from accounts.models import Booking, WorkProgress

User = get_user_model()


class ServiceCompletionTests(BaseTestCase):
    """Test service completion requirements."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_servicer_cannot_complete_without_progress(self):
        """
        Test that servicer cannot complete booking without at least one progress entry.
        Expected: Completion fails, status remains Ongoing.
        """
        # Create booking in Ongoing status with approved diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True
        )
        
        # Verify no progress entries exist
        self.assertEqual(WorkProgress.objects.filter(booking=booking).count(), 0)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Try to mark as completed (should fail - no progress)
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
        
        # Verify status is still Ongoing (not changed to Completed)
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Verify payment fields are not set
        self.assertFalse(booking.payment_requested)
        self.assertIsNone(booking.payment_status)
        self.assertIsNone(booking.final_amount)
    
    def test_completion_creates_payment_request(self):
        """
        Test that completion creates payment request.
        Expected: payment_requested=True, payment_status="Pending", final_amount is set.
        """
        # Create booking in Ongoing status with approved diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True,
            estimated_cost=5000.00
        )
        
        # Create at least one progress entry (required for completion)
        create_work_progress(
            booking=booking,
            title='Work update',
            description='Progress description',
            status='In Progress'
        )
        
        # Verify initial state
        self.assertEqual(booking.status, STATUS_ONGOING)
        self.assertFalse(booking.payment_requested)
        self.assertIsNone(booking.payment_status)
        self.assertIsNone(booking.final_amount)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Mark work as completed
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'All work completed successfully'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify status changed to Completed
        self.assertEqual(booking.status, STATUS_COMPLETED)
        
        # Verify payment request was created
        self.assertTrue(booking.payment_requested)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertEqual(str(booking.final_amount), '5500.00')
        self.assertEqual(booking.completion_notes, 'All work completed successfully')
        
        # Verify completion WorkProgress entry was created
        completion_progress = WorkProgress.objects.filter(
            booking=booking,
            title='Service Completed'
        ).first()
        self.assertIsNotNone(completion_progress)
        self.assertEqual(completion_progress.status, 'Completed')
    
    def test_completion_without_progress_notes(self):
        """
        Test that completion works even without completion_notes.
        Expected: Completion succeeds, payment request is created.
        """
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True
        )
        
        # Create progress entry
        create_work_progress(booking=booking)
        
        # Log in as servicer
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        
        # Mark work as completed without completion_notes
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5000.00',
                'completion_notes': ''  # Empty notes
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify completion succeeded
        self.assertEqual(booking.status, STATUS_COMPLETED)
        self.assertTrue(booking.payment_requested)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertEqual(str(booking.final_amount), '5000.00')


class PaymentVisibilityTests(BaseTestCase):
    """Test user can see payment requests."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_user_sees_payment_request(self):
        """
        Test that user can see payment request after completion.
        Expected: Payment appears in user_payment page.
        """
        # Create completed booking with payment request
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        
        # Set payment fields
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.final_amount = 5500.00
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access user payment page
        response = self.client.get(reverse('user_payment'))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify payment is in the list
        pending_payments = response.context['pending_payments']
        self.assertEqual(len(pending_payments), 1)
        self.assertEqual(pending_payments[0].id, booking.id)
        self.assertEqual(pending_payments[0].payment_status, PAYMENT_STATUS_PENDING)
        self.assertEqual(str(pending_payments[0].final_amount), '5500.00')
    
    def test_user_does_not_see_paid_payments(self):
        """
        Test that user does not see already paid payments in payment page.
        Expected: Only pending payments are shown.
        """
        # Create completed booking with paid payment
        paid_booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        paid_booking.payment_requested = True
        paid_booking.payment_status = PAYMENT_STATUS_PAID
        paid_booking.final_amount = 5500.00
        paid_booking.payment_date = timezone.now()
        paid_booking.save()
        
        # Create completed booking with pending payment
        pending_booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        pending_booking.payment_requested = True
        pending_booking.payment_status = PAYMENT_STATUS_PENDING
        pending_booking.final_amount = 6000.00
        pending_booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access user payment page
        response = self.client.get(reverse('user_payment'))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify only pending payment is shown
        pending_payments = response.context['pending_payments']
        self.assertEqual(len(pending_payments), 1)
        self.assertEqual(pending_payments[0].id, pending_booking.id)
        self.assertNotEqual(pending_payments[0].id, paid_booking.id)
    
    def test_user_does_not_see_other_users_payments(self):
        """
        Test that user does not see other users' payment requests.
        Expected: Only own payments are shown.
        """
        # Create another user
        other_user = create_user(
            username='other_user',
            role=ROLE_USER
        )
        
        # Create payment for other user
        other_booking = create_booking(
            user=other_user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        other_booking.payment_requested = True
        other_booking.payment_status = PAYMENT_STATUS_PENDING
        other_booking.final_amount = 5000.00
        other_booking.save()
        
        # Create payment for current user
        user_booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        user_booking.payment_requested = True
        user_booking.payment_status = PAYMENT_STATUS_PENDING
        user_booking.final_amount = 5500.00
        user_booking.save()
        
        # Log in as current user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access user payment page
        response = self.client.get(reverse('user_payment'))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify only current user's payment is shown
        pending_payments = response.context['pending_payments']
        self.assertEqual(len(pending_payments), 1)
        self.assertEqual(pending_payments[0].id, user_booking.id)
        self.assertNotEqual(pending_payments[0].id, other_booking.id)


class PaymentProcessingTests(BaseTestCase):
    """Test payment processing rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_user_can_pay_only_once(self):
        """
        Test that user can pay only once.
        Expected: Second payment attempt fails, payment_status remains "Paid".
        """
        # Create completed booking with pending payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.final_amount = 5500.00
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # First payment - should succeed
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify payment was processed
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PAID)
        self.assertIsNotNone(booking.payment_date)
        
        # Try to pay again - should fail
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        
        # Should redirect with warning
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify payment_status is still "Paid" (not changed)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PAID)
        
        # Verify payment_date is still set (not changed)
        self.assertIsNotNone(booking.payment_date)
    
    def test_user_cannot_pay_non_completed_booking(self):
        """
        Test that user cannot pay for booking that is not Completed.
        Expected: Payment fails, payment_status remains unchanged.
        """
        # Create booking in Ongoing status
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.final_amount = 5500.00
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to process payment (should fail)
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify payment_status is still Pending (not changed to Paid)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertIsNone(booking.payment_date)
    
    def test_user_cannot_pay_other_users_booking(self):
        """
        Test that user cannot pay for another user's booking.
        Expected: 404 error (get_object_or_404 ensures booking belongs to user).
        """
        # Create another user
        other_user = create_user(
            username='other_user',
            role=ROLE_USER
        )
        
        # Create completed booking for other user with pending payment
        booking = create_booking(
            user=other_user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.final_amount = 5500.00
        booking.save()
        
        # Log in as current user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to process payment for other user's booking (should fail - 404)
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        
        # Should return 404 (get_object_or_404 ensures booking belongs to user)
        self.assertEqual(response.status_code, 404)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify payment_status is still Pending (not changed)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertIsNone(booking.payment_date)


class PaymentFinalizationTests(BaseTestCase):
    """Test payment marks booking final."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_payment_marks_booking_final(self):
        """
        Test that payment marks booking as final.
        Expected: payment_status="Paid", payment_date is set, booking appears in work history.
        """
        # Create completed booking with pending payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.final_amount = 5500.00
        booking.save()
        
        # Verify initial state
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertIsNone(booking.payment_date)
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Process payment
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database
        booking.refresh_from_db()
        
        # Verify payment was processed
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PAID)
        self.assertIsNotNone(booking.payment_date)
        
        # Verify booking appears in work history
        response = self.client.get(reverse('user_work_history'))
        self.assertEqual(response.status_code, 200)
        
        completed_bookings = response.context['completed_bookings']
        self.assertEqual(len(completed_bookings), 1)
        self.assertEqual(completed_bookings[0].id, booking.id)
        self.assertEqual(completed_bookings[0].payment_status, PAYMENT_STATUS_PAID)
    
    def test_unpaid_booking_not_in_work_history(self):
        """
        Test that unpaid booking does not appear in work history.
        Expected: Only paid bookings appear in work history.
        """
        # Create completed booking with pending payment
        unpaid_booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        unpaid_booking.payment_requested = True
        unpaid_booking.payment_status = PAYMENT_STATUS_PENDING
        unpaid_booking.final_amount = 5500.00
        unpaid_booking.save()
        
        # Create completed booking with paid payment
        paid_booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        paid_booking.payment_requested = True
        paid_booking.payment_status = PAYMENT_STATUS_PAID
        paid_booking.final_amount = 6000.00
        paid_booking.payment_date = timezone.now()
        paid_booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access work history
        response = self.client.get(reverse('user_work_history'))
        self.assertEqual(response.status_code, 200)
        
        # Verify only paid booking appears
        completed_bookings = response.context['completed_bookings']
        self.assertEqual(len(completed_bookings), 1)
        self.assertEqual(completed_bookings[0].id, paid_booking.id)
        self.assertNotEqual(completed_bookings[0].id, unpaid_booking.id)


class CompletePaymentFlowTests(BaseTestCase):
    """Test complete payment flow from completion to payment."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_complete_payment_flow(self):
        """
        Test complete payment flow:
        1. Servicer completes work → payment request created
        2. User sees payment request
        3. User processes payment
        4. Booking appears in work history
        """
        # Step 1: Create booking in Ongoing status with progress
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True
        )
        
        # Create progress entry (required for completion)
        create_work_progress(booking=booking)
        
        # Step 2: Servicer completes work
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        response = self.client.post(
            reverse('mark_work_completed', args=[booking.id]),
            {
                'final_amount': '5500.00',
                'completion_notes': 'Work completed'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify payment request was created
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_COMPLETED)
        self.assertTrue(booking.payment_requested)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PENDING)
        self.assertEqual(str(booking.final_amount), '5500.00')
        
        # Step 3: User sees payment request
        self.client.logout()
        self.client.login(username=self.user.username, password='TestPass123')
        response = self.client.get(reverse('user_payment'))
        self.assertEqual(response.status_code, 200)
        pending_payments = response.context['pending_payments']
        self.assertEqual(len(pending_payments), 1)
        self.assertEqual(pending_payments[0].id, booking.id)
        
        # Step 4: User processes payment
        response = self.client.post(
            reverse('process_payment', args=[booking.id])
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify payment was processed
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PAID)
        self.assertIsNotNone(booking.payment_date)
        
        # Step 5: Booking appears in work history
        response = self.client.get(reverse('user_work_history'))
        self.assertEqual(response.status_code, 200)
        completed_bookings = response.context['completed_bookings']
        self.assertEqual(len(completed_bookings), 1)
        self.assertEqual(completed_bookings[0].id, booking.id)
        self.assertEqual(completed_bookings[0].payment_status, PAYMENT_STATUS_PAID)
