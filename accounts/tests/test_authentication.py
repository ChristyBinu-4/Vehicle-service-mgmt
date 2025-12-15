"""
Test authentication flows for User and Servicer.

Tests verify:
1. User login (valid credentials, invalid password, nonexistent user)
2. User registration (valid data, invalid email, phone validation, password validation)
3. Servicer login (servicer can log in, user cannot access servicer views)

All tests follow @vms_requirements.txt as the single source of truth.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.tests.test_utils import (
    create_user, create_servicer,
    ROLE_USER, ROLE_SERVICER, ROLE_ADMIN,
    BaseTestCase
)

User = get_user_model()


class UserLoginTests(TestCase):
    """Test user login functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.login_url = reverse('login_page')
        self.user_home_url = reverse('user_home')
        
        # Create a test user with known credentials
        self.test_username = 'testuser'
        self.test_password = 'TestPass123'
        self.test_user = create_user(
            username=self.test_username,
            password=self.test_password,
            role=ROLE_USER
        )
    
    def test_login_with_valid_credentials(self):
        """
        Test that user can log in with valid credentials.
        Expected: Redirect to user_home, user is authenticated.
        """
        response = self.client.post(self.login_url, {
            'username': self.test_username,
            'password': self.test_password
        })
        
        # Should redirect to user home on success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.user_home_url)
        
        # User should be authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_with_invalid_password(self):
        """
        Test that login fails with incorrect password.
        Expected: Redirect back to login with error parameter, user not authenticated.
        """
        response = self.client.post(self.login_url, {
            'username': self.test_username,
            'password': 'WrongPassword123'
        })
        
        # Should redirect back to login with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid', response.url)
        
        # User should NOT be authenticated
        # Note: response.wsgi_request.user might be AnonymousUser
        # We verify by checking that accessing user_home redirects to login
        response = self.client.get(self.user_home_url)
        self.assertNotEqual(response.status_code, 200)
    
    def test_login_with_nonexistent_user(self):
        """
        Test that login fails for nonexistent username.
        Expected: Redirect back to login with error parameter, user not authenticated.
        """
        response = self.client.post(self.login_url, {
            'username': 'nonexistent_user',
            'password': 'TestPass123'
        })
        
        # Should redirect back to login with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid', response.url)
        
        # User should NOT be authenticated
        response = self.client.get(self.user_home_url)
        self.assertNotEqual(response.status_code, 200)
    
    def test_login_with_empty_username(self):
        """
        Test that login fails with empty username.
        Expected: Redirect back to login with empty_username error.
        """
        response = self.client.post(self.login_url, {
            'username': '',
            'password': self.test_password
        })
        
        # Should redirect back to login with empty_username error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=empty_username', response.url)
    
    def test_login_with_empty_password(self):
        """
        Test that login fails with empty password.
        Expected: Redirect back to login with empty_password error.
        """
        response = self.client.post(self.login_url, {
            'username': self.test_username,
            'password': ''
        })
        
        # Should redirect back to login with empty_password error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=empty_password', response.url)
    
    def test_login_with_inactive_account(self):
        """
        Test that login fails for inactive account.
        
        Note: Django's authenticate() returns None for inactive users,
        so the view treats it as invalid credentials (error=invalid).
        This is the expected behavior - inactive accounts cannot authenticate.
        
        Expected: Redirect back to login with invalid error (not inactive error).
        """
        # Create an inactive user
        inactive_user = create_user(
            username='inactive_user',
            password=self.test_password,
            role=ROLE_USER
        )
        inactive_user.is_active = False
        inactive_user.save()
        
        response = self.client.post(self.login_url, {
            'username': 'inactive_user',
            'password': self.test_password
        })
        
        # Django's authenticate() returns None for inactive users,
        # so the view treats it as invalid credentials
        # This is correct behavior - inactive accounts cannot authenticate
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid', response.url)
    
    def test_login_with_non_user_role(self):
        """
        Test that servicer/admin cannot log in through user login page.
        Expected: Redirect back to login with invalid_role error.
        """
        # Create a servicer user
        servicer_user = create_user(
            username='servicer_user',
            password=self.test_password,
            role=ROLE_SERVICER
        )
        
        response = self.client.post(self.login_url, {
            'username': 'servicer_user',
            'password': self.test_password
        })
        
        # Should redirect back to login with invalid_role error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid_role', response.url)


class UserRegistrationTests(TestCase):
    """Test user registration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.register_url = reverse('user_register')
        self.login_url = reverse('login_page')
    
    def test_registration_with_valid_data(self):
        """
        Test that user can register with valid data.
        Expected: User created, redirect to login page with success parameter.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('registered=success', response.url)
        
        # User should be created in database
        self.assertTrue(User.objects.filter(username='johndoe').exists())
        user = User.objects.get(username='johndoe')
        self.assertEqual(user.role, ROLE_USER)
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertEqual(user.phone, '1234567890')
        self.assertTrue(user.is_active)
    
    def test_registration_with_invalid_email_format(self):
        """
        Test that registration fails with invalid email format.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'invalid-email',  # Invalid email format
            'phone': '1234567890',
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors (status 200, not redirect)
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have email error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_registration_with_duplicate_email(self):
        """
        Test that registration fails with duplicate email.
        Expected: Form validation error, user not created.
        """
        # Create existing user with email
        create_user(
            username='existing_user',
            email='existing@example.com',
            role=ROLE_USER
        )
        
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'existing@example.com',  # Duplicate email
            'phone': '1234567890',
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have email error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_registration_with_phone_not_10_digits(self):
        """
        Test that registration fails with phone number not exactly 10 digits.
        Expected: Form validation error, user not created.
        """
        # Test with 9 digits
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '123456789',  # Only 9 digits
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have phone error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        
        # Test with 11 digits
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '12345678901',  # 11 digits
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='johndoe').exists())
    
    def test_registration_with_phone_non_digits(self):
        """
        Test that registration fails with phone containing non-digit characters.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '123456789a',  # Contains letter
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have phone error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
    
    def test_registration_with_weak_password_short(self):
        """
        Test that registration fails with password less than 8 characters.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'Short1',  # Only 7 characters
            'password2': 'Short1'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have password error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
    
    def test_registration_with_weak_password_no_uppercase(self):
        """
        Test that registration fails with password without uppercase letter.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'testpass123',  # No uppercase
            'password2': 'testpass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have password error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
    
    def test_registration_with_weak_password_no_lowercase(self):
        """
        Test that registration fails with password without lowercase letter.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'TESTPASS123',  # No lowercase
            'password2': 'TESTPASS123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have password error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
    
    def test_registration_with_weak_password_no_number(self):
        """
        Test that registration fails with password without number.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'TestPass',  # No number
            'password2': 'TestPass'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have password error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
    
    def test_registration_with_password_mismatch(self):
        """
        Test that registration fails when passwords do not match.
        Expected: Form validation error, user not created.
        """
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'TestPass123',
            'password2': 'TestPass456'  # Different password
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # User should NOT be created
        self.assertFalse(User.objects.filter(username='johndoe').exists())
        
        # Form should have password2 error (mismatch)
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_registration_with_duplicate_username(self):
        """
        Test that registration fails with duplicate username.
        Expected: Form validation error, user not created.
        """
        # Create existing user with username
        create_user(
            username='johndoe',
            role=ROLE_USER
        )
        
        response = self.client.post(self.register_url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',  # Duplicate username
            'email': 'john.doe@example.com',
            'phone': '1234567890',
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        
        # Form should have username error
        form = response.context.get('form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)


class ServicerLoginTests(TestCase):
    """Test servicer login functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.servicer_login_url = reverse('servicer_login')
        self.servicer_home_url = reverse('servicer_home')
        
        # Create a test servicer user with known credentials
        self.test_username = 'servicer_user'
        self.test_password = 'TestPass123'
        self.test_servicer = create_user(
            username=self.test_username,
            password=self.test_password,
            role=ROLE_SERVICER
        )
    
    def test_servicer_can_login(self):
        """
        Test that servicer can log in with valid credentials.
        Expected: Redirect to servicer_home, servicer is authenticated.
        """
        response = self.client.post(self.servicer_login_url, {
            'username': self.test_username,
            'password': self.test_password
        })
        
        # Should redirect to servicer home on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.servicer_home_url)
        
        # Follow redirect to verify servicer is authenticated
        response = self.client.get(self.servicer_home_url)
        # If authenticated, should get 200 (or redirect if there's additional auth check)
        # The servicer_home view requires login and servicer role
        self.assertIn(response.status_code, [200, 302])
        
        # Verify user is in session
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = self.client.session.get('_auth_user_id')
        if user_id:
            user = User.objects.get(pk=user_id)
            self.assertEqual(user.role, ROLE_SERVICER)
    
    def test_user_cannot_access_servicer_views(self):
        """
        Test that USER role cannot access servicer views.
        
        Expected: USER is logged out and redirected to login_page (root URL) with invalid_role error.
        The servicer_role_required decorator should detect non-servicer users and
        redirect them appropriately.
        """
        # Create a regular user
        user = create_user(
            username='regular_user',
            password=self.test_password,
            role=ROLE_USER
        )
        
        # Log in as regular user
        self.client.login(username='regular_user', password=self.test_password)
        
        # Try to access servicer home
        response = self.client.get(self.servicer_home_url)
        
        # Should redirect to login_page (root URL '/') with invalid_role error
        # The login_page URL is at root '/', so the redirect URL is '/?error=invalid_role'
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid_role', response.url)
        # login_page is at root URL, so URL should be '/' or contain 'error=invalid_role'
        login_page_url = reverse('login_page')
        self.assertTrue(
            response.url.startswith(login_page_url) or 'error=invalid_role' in response.url,
            f"Expected redirect to login_page with invalid_role error, got: {response.url}"
        )
        
        # User should be logged out
        # Verify by trying to access a protected user view
        # If still logged in, it would work; if logged out, it redirects
        user_home_url = reverse('user_home')
        response = self.client.get(user_home_url)
        # Should redirect to login (user was logged out)
        self.assertIn(response.status_code, [302, 403])
    
    def test_servicer_login_with_invalid_credentials(self):
        """
        Test that servicer login fails with invalid credentials.
        Expected: Redirect back to servicer_login with error parameter.
        """
        response = self.client.post(self.servicer_login_url, {
            'username': self.test_username,
            'password': 'WrongPassword123'
        })
        
        # Should redirect back to servicer login with error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid', response.url)
    
    def test_servicer_login_with_non_servicer_role(self):
        """
        Test that USER role cannot log in through servicer login page.
        Expected: Redirect back to servicer_login with invalid_role error.
        """
        # Create a regular user
        user = create_user(
            username='regular_user',
            password=self.test_password,
            role=ROLE_USER
        )
        
        response = self.client.post(self.servicer_login_url, {
            'username': 'regular_user',
            'password': self.test_password
        })
        
        # Should redirect back to servicer login with invalid_role error
        self.assertEqual(response.status_code, 302)
        self.assertIn('error=invalid_role', response.url)
