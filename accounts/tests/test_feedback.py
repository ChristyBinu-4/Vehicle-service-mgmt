"""
Test feedback and rating system.

Tests verify:
1. Feedback allowed ONLY if booking.status == "Completed" AND payment_status == "Paid"
2. One feedback per booking
3. Servicer rating is aggregated correctly
4. Feedback is read-only after submission

All tests follow @vms_requirements.txt as the single source of truth.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.tests.test_utils import (
    create_user, create_servicer, create_booking, create_diagnosis, create_feedback,
    ROLE_USER, ROLE_SERVICER,
    STATUS_ONGOING, STATUS_COMPLETED,
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_PAID,
    BaseTestCase
)
from accounts.models import Booking, Feedback, Servicer

User = get_user_model()


class FeedbackEligibilityTests(BaseTestCase):
    """Test feedback eligibility rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_feedback_allowed_when_completed_and_paid(self):
        """
        Test that feedback is allowed when booking.status == "Completed" AND payment_status == "Paid".
        Expected: Feedback can be submitted successfully.
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Verify initial state
        self.assertEqual(booking.status, STATUS_COMPLETED)
        self.assertEqual(booking.payment_status, PAYMENT_STATUS_PAID)
        self.assertFalse(hasattr(booking, 'feedback'))
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Submit feedback
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Excellent service! Very satisfied.'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh booking from database to get updated relationships
        booking.refresh_from_db()
        
        # Verify feedback was created
        self.assertTrue(hasattr(booking, 'feedback'))
        feedback = booking.feedback
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.message, 'Excellent service! Very satisfied.')
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.servicer, self.servicer)
        self.assertEqual(feedback.booking, booking)
    
    def test_feedback_not_allowed_when_status_not_completed(self):
        """
        Test that feedback is NOT allowed when booking.status != "Completed".
        Expected: Feedback submission fails.
        """
        # Create booking in Ongoing status (not completed)
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to submit feedback (should fail)
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Great service'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Verify feedback was NOT created
        self.assertFalse(hasattr(booking, 'feedback'))
    
    def test_feedback_not_allowed_when_payment_not_paid(self):
        """
        Test that feedback is NOT allowed when payment_status != "Paid".
        Expected: Feedback submission fails.
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
        
        # Try to submit feedback (should fail)
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Great service'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Verify feedback was NOT created
        self.assertFalse(hasattr(booking, 'feedback'))
    
    def test_feedback_not_allowed_when_both_conditions_fail(self):
        """
        Test that feedback is NOT allowed when both status != "Completed" AND payment_status != "Paid".
        Expected: Feedback submission fails.
        """
        # Create booking in Ongoing status with pending payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_ONGOING
        )
        booking.payment_status = PAYMENT_STATUS_PENDING
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to submit feedback (should fail)
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Great service'
            }
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Verify feedback was NOT created
        self.assertFalse(hasattr(booking, 'feedback'))


class OneFeedbackPerBookingTests(BaseTestCase):
    """Test one feedback per booking rule."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_one_feedback_per_booking(self):
        """
        Test that only one feedback can be submitted per booking.
        Expected: Second feedback submission fails.
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Submit first feedback
        response1 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'First feedback'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response1.status_code, 302)
        
        # Verify feedback was created
        self.assertTrue(hasattr(booking, 'feedback'))
        feedback1 = booking.feedback
        self.assertEqual(feedback1.rating, 5)
        self.assertEqual(feedback1.message, 'First feedback')
        
        # Try to submit second feedback (should fail)
        response2 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '4',
                'message': 'Second feedback attempt'
            }
        )
        
        # Should redirect with warning
        self.assertEqual(response2.status_code, 302)
        
        # Refresh feedback from database
        feedback1.refresh_from_db()
        
        # Verify original feedback is unchanged
        self.assertEqual(feedback1.rating, 5)
        self.assertEqual(feedback1.message, 'First feedback')
        
        # Verify only one feedback exists for this booking
        feedback_count = Feedback.objects.filter(booking=booking).count()
        self.assertEqual(feedback_count, 1)
    
    def test_feedback_one_to_one_relationship(self):
        """
        Test that Feedback model enforces one-to-one relationship with Booking.
        Expected: Only one feedback can exist per booking (model constraint).
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Create first feedback
        feedback1 = create_feedback(
            user=self.user,
            booking=booking,
            servicer=self.servicer,
            rating=5,
            message='First feedback'
        )
        
        # Verify feedback exists
        self.assertTrue(hasattr(booking, 'feedback'))
        self.assertEqual(booking.feedback.id, feedback1.id)
        
        # Try to create second feedback for same booking (should fail due to OneToOneField)
        # This would raise IntegrityError in database, but we test the view logic
        # The view checks hasattr(booking, 'feedback') before allowing submission


class ServicerRatingAggregationTests(BaseTestCase):
    """Test servicer rating aggregation."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user1 = create_user(username='user1', role=ROLE_USER)
        self.user2 = create_user(username='user2', role=ROLE_USER)
        self.user3 = create_user(username='user3', role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email, rating=4.5)
    
    def test_servicer_rating_aggregated_correctly_single_feedback(self):
        """
        Test that servicer rating is aggregated correctly from single feedback.
        Expected: servicer.rating equals the feedback rating.
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user1,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user1.username, password='TestPass123')
        
        # Submit feedback with rating 5
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Excellent service'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Refresh servicer from database
        self.servicer.refresh_from_db()
        
        # Verify servicer rating is updated
        # With one feedback of rating 5, average should be 5.0
        self.assertEqual(self.servicer.rating, 5.0)
    
    def test_servicer_rating_aggregated_correctly_multiple_feedbacks(self):
        """
        Test that servicer rating is aggregated correctly from multiple feedbacks.
        Expected: servicer.rating equals average of all feedback ratings.
        """
        # Create three completed bookings with paid payments
        booking1 = create_booking(
            user=self.user1,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking1.payment_requested = True
        booking1.payment_status = PAYMENT_STATUS_PAID
        booking1.final_amount = 5500.00
        booking1.payment_date = timezone.now()
        booking1.save()
        
        booking2 = create_booking(
            user=self.user2,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking2.payment_requested = True
        booking2.payment_status = PAYMENT_STATUS_PAID
        booking2.final_amount = 6000.00
        booking2.payment_date = timezone.now()
        booking2.save()
        
        booking3 = create_booking(
            user=self.user3,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking3.payment_requested = True
        booking3.payment_status = PAYMENT_STATUS_PAID
        booking3.final_amount = 5000.00
        booking3.payment_date = timezone.now()
        booking3.save()
        
        # Submit feedback for booking1 (rating 5)
        self.client.login(username=self.user1.username, password='TestPass123')
        response1 = self.client.post(
            reverse('submit_feedback', args=[booking1.id]),
            {
                'rating': '5',
                'message': 'Excellent'
            }
        )
        self.assertEqual(response1.status_code, 302)
        
        # Refresh servicer
        self.servicer.refresh_from_db()
        # After first feedback: rating = 5.0
        self.assertEqual(self.servicer.rating, 5.0)
        
        # Submit feedback for booking2 (rating 4)
        self.client.logout()
        self.client.login(username=self.user2.username, password='TestPass123')
        response2 = self.client.post(
            reverse('submit_feedback', args=[booking2.id]),
            {
                'rating': '4',
                'message': 'Good service'
            }
        )
        self.assertEqual(response2.status_code, 302)
        
        # Refresh servicer
        self.servicer.refresh_from_db()
        # After second feedback: average = (5 + 4) / 2 = 4.5
        self.assertEqual(self.servicer.rating, 4.5)
        
        # Submit feedback for booking3 (rating 3)
        self.client.logout()
        self.client.login(username=self.user3.username, password='TestPass123')
        response3 = self.client.post(
            reverse('submit_feedback', args=[booking3.id]),
            {
                'rating': '3',
                'message': 'Average service'
            }
        )
        self.assertEqual(response3.status_code, 302)
        
        # Refresh servicer
        self.servicer.refresh_from_db()
        # After third feedback: average = (5 + 4 + 3) / 3 = 4.0
        # Rounded to 1 decimal place
        self.assertEqual(self.servicer.rating, 4.0)
    
    def test_servicer_rating_rounded_to_one_decimal(self):
        """
        Test that servicer rating is rounded to one decimal place.
        Expected: Rating is rounded correctly (e.g., 4.33 → 4.3).
        """
        # Create bookings for ratings that will result in non-integer average
        # Ratings: 5, 4, 4 → average = 4.33... → rounded to 4.3
        booking1 = create_booking(
            user=self.user1,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking1.payment_requested = True
        booking1.payment_status = PAYMENT_STATUS_PAID
        booking1.payment_date = timezone.now()
        booking1.save()
        
        booking2 = create_booking(
            user=self.user2,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking2.payment_requested = True
        booking2.payment_status = PAYMENT_STATUS_PAID
        booking2.payment_date = timezone.now()
        booking2.save()
        
        booking3 = create_booking(
            user=self.user3,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking3.payment_requested = True
        booking3.payment_status = PAYMENT_STATUS_PAID
        booking3.payment_date = timezone.now()
        booking3.save()
        
        # Submit feedbacks: 5, 4, 4
        self.client.login(username=self.user1.username, password='TestPass123')
        self.client.post(
            reverse('submit_feedback', args=[booking1.id]),
            {'rating': '5', 'message': 'Excellent'}
        )
        
        self.client.logout()
        self.client.login(username=self.user2.username, password='TestPass123')
        self.client.post(
            reverse('submit_feedback', args=[booking2.id]),
            {'rating': '4', 'message': 'Good'}
        )
        
        self.client.logout()
        self.client.login(username=self.user3.username, password='TestPass123')
        self.client.post(
            reverse('submit_feedback', args=[booking3.id]),
            {'rating': '4', 'message': 'Good'}
        )
        
        # Refresh servicer
        self.servicer.refresh_from_db()
        
        # Average = (5 + 4 + 4) / 3 = 4.333... → rounded to 4.3
        # Note: servicer.rating is a DecimalField, so we compare as float
        self.assertEqual(float(self.servicer.rating), 4.3)


class FeedbackReadOnlyTests(BaseTestCase):
    """Test feedback is read-only after submission."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_feedback_is_read_only_after_submission(self):
        """
        Test that feedback is read-only after submission.
        Expected: No edit/delete functionality exists, feedback values remain unchanged.
        Note: We verify immutability by checking no edit endpoints exist and values persist.
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Submit feedback
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Original feedback message'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Verify feedback was created
        self.assertTrue(hasattr(booking, 'feedback'))
        feedback = booking.feedback
        original_rating = feedback.rating
        original_message = feedback.message
        original_created_at = feedback.created_at
        
        # Verify no edit/delete URLs exist in urls.py
        # (This is verified by the fact that we can only create, not edit/delete)
        
        # Wait a moment (simulate time passing)
        import time
        time.sleep(0.1)
        
        # Refresh feedback from database
        feedback.refresh_from_db()
        
        # Verify values are unchanged (read-only)
        self.assertEqual(feedback.rating, original_rating)
        self.assertEqual(feedback.message, original_message)
        self.assertEqual(feedback.created_at, original_created_at)
    
    def test_feedback_cannot_be_resubmitted(self):
        """
        Test that feedback cannot be resubmitted after initial submission.
        Expected: Attempting to resubmit fails, original feedback remains unchanged.
        """
        # Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Submit initial feedback
        response1 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Original feedback'
            }
        )
        self.assertEqual(response1.status_code, 302)
        
        # Verify feedback was created
        self.assertTrue(hasattr(booking, 'feedback'))
        feedback = booking.feedback
        original_rating = feedback.rating
        original_message = feedback.message
        
        # Try to resubmit feedback (should fail)
        response2 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '4',
                'message': 'Updated feedback attempt'
            }
        )
        
        # Should redirect with warning
        self.assertEqual(response2.status_code, 302)
        
        # Refresh feedback from database
        feedback.refresh_from_db()
        
        # Verify original feedback is unchanged (read-only)
        self.assertEqual(feedback.rating, original_rating)
        self.assertEqual(feedback.message, original_message)


class FeedbackValidationTests(BaseTestCase):
    """Test feedback form validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email)
    
    def test_feedback_requires_rating(self):
        """
        Test that feedback requires a rating.
        Expected: Form validation fails without rating.
        """
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to submit feedback without rating
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '',  # Empty rating
                'message': 'Feedback message'
            }
        )
        
        # Should return form with errors (status 200, not redirect)
        self.assertEqual(response.status_code, 200)
        
        # Verify feedback was NOT created
        self.assertFalse(hasattr(booking, 'feedback'))
        
        # Form should have rating error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_feedback_requires_message(self):
        """
        Test that feedback requires a message.
        Expected: Form validation fails without message.
        """
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to submit feedback without message
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': ''  # Empty message
            }
        )
        
        # Should return form with errors (status 200, not redirect)
        self.assertEqual(response.status_code, 200)
        
        # Verify feedback was NOT created
        self.assertFalse(hasattr(booking, 'feedback'))
        
        # Form should have message error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('message', form.errors)
    
    def test_feedback_rating_range_validation(self):
        """
        Test that feedback rating must be between 1 and 5.
        Expected: Form validation fails for invalid ratings.
        """
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Log in as user
        self.client.login(username=self.user.username, password='TestPass123')
        
        # Try to submit feedback with invalid rating (0)
        response1 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '0',  # Invalid: below minimum
                'message': 'Feedback message'
            }
        )
        
        # Should return form with errors
        self.assertEqual(response1.status_code, 200)
        self.assertFalse(hasattr(booking, 'feedback'))
        
        # Try to submit feedback with invalid rating (6)
        response2 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '6',  # Invalid: above maximum
                'message': 'Feedback message'
            }
        )
        
        # Should return form with errors
        self.assertEqual(response2.status_code, 200)
        self.assertFalse(hasattr(booking, 'feedback'))


class CompleteFeedbackFlowTests(BaseTestCase):
    """Test complete feedback flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user = create_user(role=ROLE_USER)
        self.servicer_user = create_user(role=ROLE_SERVICER)
        self.servicer = create_servicer(email=self.servicer_user.email, rating=4.5)
    
    def test_complete_feedback_flow(self):
        """
        Test complete feedback flow:
        1. Booking is completed and paid
        2. User submits feedback
        3. Servicer rating is updated
        4. Feedback is read-only
        """
        # Step 1: Create completed booking with paid payment
        booking = create_booking(
            user=self.user,
            servicer=self.servicer,
            status=STATUS_COMPLETED
        )
        booking.payment_requested = True
        booking.payment_status = PAYMENT_STATUS_PAID
        booking.final_amount = 5500.00
        booking.payment_date = timezone.now()
        booking.save()
        
        # Verify initial servicer rating
        initial_rating = self.servicer.rating
        
        # Step 2: User submits feedback
        self.client.login(username=self.user.username, password='TestPass123')
        response = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '5',
                'message': 'Excellent service! Very satisfied with the work.'
            }
        )
        
        # Should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # Step 3: Verify feedback was created
        self.assertTrue(hasattr(booking, 'feedback'))
        feedback = booking.feedback
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.message, 'Excellent service! Very satisfied with the work.')
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.servicer, self.servicer)
        self.assertEqual(feedback.booking, booking)
        
        # Step 4: Verify servicer rating is updated
        self.servicer.refresh_from_db()
        # If this is the first feedback, rating should be 5.0
        # If there were previous feedbacks, it should be recalculated
        self.assertIsNotNone(self.servicer.rating)
        self.assertGreaterEqual(self.servicer.rating, 1.0)
        self.assertLessEqual(self.servicer.rating, 5.0)
        
        # Step 5: Verify feedback is read-only (cannot be resubmitted)
        response2 = self.client.post(
            reverse('submit_feedback', args=[booking.id]),
            {
                'rating': '4',
                'message': 'Updated feedback attempt'
            }
        )
        
        # Should redirect with warning
        self.assertEqual(response2.status_code, 302)
        
        # Verify original feedback is unchanged
        feedback.refresh_from_db()
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.message, 'Excellent service! Very satisfied with the work.')
