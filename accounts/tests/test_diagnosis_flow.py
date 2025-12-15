"""
Test diagnosis visibility and approval rules.

Tests verify:
1. Diagnosis is NOT visible:
   - Before servicer submits it
   - When booking is Requested
2. Diagnosis IS visible:
   - When status is Pending
   - After servicer submission
3. User approval:
   - Allowed only once
   - Changes status to Ongoing
   - Cannot be repeated

All tests follow @vms_requirements.txt as the single source of truth.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.tests.test_utils import (
    create_user, create_servicer, create_booking, create_diagnosis,
    ROLE_USER, ROLE_SERVICER,
    STATUS_REQUESTED, STATUS_PENDING, STATUS_ONGOING,
    BaseTestCase
)
from accounts.models import Booking, Diagnosis

User = get_user_model()


class DiagnosisVisibilityTests(BaseTestCase):
    """Test diagnosis visibility rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_diagnosis_not_visible_before_servicer_submits(self):
        """
        Test that diagnosis is NOT visible before servicer submits it.
        Expected: diagnosis_visible is False when no diagnosis exists.
        """
        # Create booking in Pending status (after acceptance)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Verify no diagnosis exists
        self.assertFalse(hasattr(booking, 'diagnosis'))
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis_visible is False in context
        self.assertFalse(response.context['diagnosis_visible'])
        self.assertIsNone(response.context.get('diagnosis'))
        
        # Verify Diagnostics tab is NOT in the rendered HTML
        # (We check the context variable, which controls template rendering)
        self.assertFalse(response.context['diagnosis_visible'])
    
    def test_diagnosis_not_visible_when_booking_is_requested(self):
        """
        Test that diagnosis is NOT visible when booking status is "Requested".
        Expected: diagnosis_visible is False even if diagnosis exists (edge case).
        """
        # Create booking in Requested status
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_REQUESTED
        )
        
        # Create diagnosis (edge case - shouldn't happen in normal flow)
        diagnosis = create_diagnosis(booking=booking)
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis_visible is False (status is not Pending)
        # The view logic checks: if booking.status == "Pending" AND diagnosis exists
        self.assertFalse(response.context['diagnosis_visible'])
        
        # Even though diagnosis exists, it should not be visible because status is Requested
        # The view sets diagnosis_visible = False when status != "Pending"
    
    def test_diagnosis_visible_when_status_is_pending_and_exists(self):
        """
        Test that diagnosis IS visible when status is Pending and diagnosis exists.
        Expected: diagnosis_visible is True, diagnosis is in context.
        """
        # Create booking in Pending status
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Create diagnosis
        diagnosis = create_diagnosis(
            booking=booking,
            report='Diagnosis report',
            work_items='Oil change, Filter replacement',
            estimated_cost=5000.00
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis_visible is True
        self.assertTrue(response.context['diagnosis_visible'])
        
        # Verify diagnosis is in context
        self.assertIsNotNone(response.context.get('diagnosis'))
        self.assertEqual(response.context['diagnosis'].id, diagnosis.id)
        self.assertEqual(response.context['diagnosis'].report, 'Diagnosis report')
    
    def test_diagnosis_not_visible_when_status_is_ongoing(self):
        """
        Test that diagnosis is NOT visible when booking status is "Ongoing".
        Expected: diagnosis_visible is False even if diagnosis exists.
        """
        # Create booking in Ongoing status (after approval)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        
        # Create diagnosis (already approved)
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis_visible is False (status is not Pending)
        # The view only shows diagnosis when status == "Pending"
        self.assertFalse(response.context['diagnosis_visible'])


class DiagnosisApprovalTests(BaseTestCase):
    """Test diagnosis approval rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_user_approval_changes_status_to_ongoing(self):
        """
        Test that user approval changes booking status to "Ongoing".
        Expected: Status changes from "Pending" to "Ongoing", diagnosis.user_approved = True.
        """
        # Create booking in Pending status with diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=False
        )
        
        # Verify initial state
        self.assertEqual(booking.status, STATUS_PENDING)
        self.assertFalse(diagnosis.user_approved)
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Approve diagnosis
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking and diagnosis from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status changed to Ongoing
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Verify diagnosis is approved
        self.assertTrue(diagnosis.user_approved)
    
    def test_user_approval_allowed_only_once(self):
        """
        Test that user approval is allowed only once.
        Expected: Second approval attempt fails, status remains Ongoing.
        """
        # Create booking in Pending status with diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=False
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # First approval - should succeed
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify first approval worked
        self.assertEqual(booking.status, STATUS_ONGOING)
        self.assertTrue(diagnosis.user_approved)
        
        # Try to approve again - should fail
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should redirect (with warning message)
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status is still Ongoing (not changed)
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Verify diagnosis is still approved
        self.assertTrue(diagnosis.user_approved)
    
    def test_user_cannot_approve_when_status_not_pending(self):
        """
        Test that user cannot approve diagnosis when booking status is not "Pending".
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
            user_approved=True
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to approve (should fail - status is not Pending)
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status is still Ongoing (not changed)
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Verify diagnosis is still approved
        self.assertTrue(diagnosis.user_approved)
    
    def test_user_cannot_approve_when_diagnosis_not_exists(self):
        """
        Test that user cannot approve diagnosis when diagnosis does not exist.
        Expected: Approval fails, status remains unchanged.
        """
        # Create booking in Pending status without diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Verify no diagnosis exists
        self.assertFalse(hasattr(booking, 'diagnosis'))
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to approve (should fail - no diagnosis)
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Refresh from database
        booking.refresh_from_db()
        
        # Verify status is still Pending (not changed)
        self.assertEqual(booking.status, STATUS_PENDING)
    
    def test_user_cannot_approve_other_users_booking(self):
        """
        Test that user cannot approve diagnosis for another user's booking.
        Expected: 404 error (get_object_or_404 ensures booking belongs to user).
        """
        # Create another user
        other_user = create_user(
            username='other_user',
            role=ROLE_USER
        )
        
        # Create booking for other user
        booking = create_booking(
            user=other_user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        diagnosis = create_diagnosis(booking=booking)
        
        # Log in as first user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to approve other user's booking (should fail - 404)
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        
        # Should return 404 (get_object_or_404 ensures booking belongs to user)
        self.assertEqual(response.status_code, 404)
        
        # Refresh from database
        booking.refresh_from_db()
        diagnosis.refresh_from_db()
        
        # Verify status is still Pending (not changed)
        self.assertEqual(booking.status, STATUS_PENDING)
        self.assertFalse(diagnosis.user_approved)


class DiagnosisApprovalButtonVisibilityTests(BaseTestCase):
    """Test that approve button visibility follows rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_approve_button_visible_when_diagnosis_not_approved(self):
        """
        Test that approve button is visible when diagnosis exists and is not approved.
        Expected: Button should be visible in template context.
        Note: We test the view logic that controls button visibility.
        """
        # Create booking in Pending status with unapproved diagnosis
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=False
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis is visible and not approved
        self.assertTrue(response.context['diagnosis_visible'])
        self.assertIsNotNone(response.context.get('diagnosis'))
        self.assertFalse(response.context['diagnosis'].user_approved)
        
        # The template shows approve button when: diagnosis_visible AND not diagnosis.user_approved
        # Both conditions are met, so button should be visible
    
    def test_approve_button_not_visible_when_diagnosis_already_approved(self):
        """
        Test that approve button is NOT visible when diagnosis is already approved.
        Expected: Button should not be visible (diagnosis.user_approved = True).
        """
        # Create booking in Pending status with approved diagnosis
        # Note: This is an edge case - normally status would be Ongoing after approval
        # But we test the button visibility logic
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        diagnosis = create_diagnosis(
            booking=booking,
            user_approved=True  # Already approved
        )
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Access booking detail page
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        # Verify diagnosis is visible
        self.assertTrue(response.context['diagnosis_visible'])
        self.assertIsNotNone(response.context.get('diagnosis'))
        
        # Verify diagnosis is already approved
        self.assertTrue(response.context['diagnosis'].user_approved)
        
        # The template shows approve button only when: diagnosis_visible AND not diagnosis.user_approved
        # Since user_approved = True, button should NOT be visible


class CompleteDiagnosisFlowTests(BaseTestCase):
    """Test complete diagnosis flow from submission to approval."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_complete_diagnosis_flow(self):
        """
        Test complete diagnosis flow:
        1. Booking in Pending status
        2. Diagnosis not visible (not yet submitted)
        3. Servicer submits diagnosis
        4. Diagnosis becomes visible
        5. User approves diagnosis
        6. Status changes to Ongoing
        7. Diagnosis no longer visible (status is not Pending)
        """
        # Step 1: Create booking in Pending status (after acceptance)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_PENDING
        )
        
        # Step 2: Verify diagnosis not visible (not yet submitted)
        self.client.login(username=self.user.username, password='TestPass123')
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['diagnosis_visible'])
        self.assertIsNone(response.context.get('diagnosis'))
        
        # Step 3: Servicer submits diagnosis
        self.client.logout()
        self.client.login(username=self.servicer_user.username, password='TestPass123')
        response = self.client.post(
            reverse('create_diagnosis', args=[booking.id]),
            {
                'report': 'Complete diagnosis report',
                'work_items': 'Oil change, Filter replacement, Brake check',
                'estimated_cost': '6000.00',
                'estimated_completion_time': '3 days'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # Step 4: Verify diagnosis is now visible
        self.client.logout()
        self.client.login(username=self.user.username, password='TestPass123')
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['diagnosis_visible'])
        self.assertIsNotNone(response.context.get('diagnosis'))
        self.assertFalse(response.context['diagnosis'].user_approved)
        
        # Step 5: User approves diagnosis
        response = self.client.post(
            reverse('approve_diagnosis', args=[booking.id])
        )
        self.assertEqual(response.status_code, 302)
        
        # Step 6: Verify status changed to Ongoing
        booking.refresh_from_db()
        self.assertEqual(booking.status, STATUS_ONGOING)
        
        # Step 7: Verify diagnosis no longer visible (status is not Pending)
        response = self.client.get(reverse('booking_detail', args=[booking.id]))
        self.assertEqual(response.status_code, 200)
        # Diagnosis should not be visible when status is Ongoing
        self.assertFalse(response.context['diagnosis_visible'])
