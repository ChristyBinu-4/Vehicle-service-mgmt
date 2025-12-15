from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.http import HttpResponseRedirect
from functools import wraps

from .forms import (
    UserRegisterForm, FeedbackForm, ProfileUpdateForm, PasswordChangeForm, 
    ServicerRegisterForm, ServicerProfileUpdateForm, RejectBookingForm, 
    AcceptBookingForm, DiagnosisForm, ProgressUpdateForm, CompleteWorkForm
)
from .models import Feedback, WorkProgress, Servicer, Booking, Diagnosis


def user_role_required(view_func):
    """
    Decorator to ensure only users with USER role can access the view.
    Must be used after @login_required decorator.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_page')
        
        if request.user.role != 'USER':
            # User is logged in but not a USER role
            logout(request)
            return HttpResponseRedirect(reverse("login_page") + "?error=invalid_role")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def servicer_role_required(view_func):
    """
    Decorator to ensure only users with SERVICER role can access the view.
    Must be used after @login_required decorator.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('servicer_login')
        
        if request.user.role != 'SERVICER':
            # User is logged in but not a SERVICER role
            logout(request)
            if request.user.role == 'USER':
                return HttpResponseRedirect(reverse("login_page") + "?error=invalid_role")
            else:
                return HttpResponseRedirect(reverse("servicer_login") + "?error=invalid_role")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_role_required(view_func):
    """
    Decorator to ensure only users with ADMIN role can access the view.
    Must be used after @login_required decorator.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        
        if request.user.role != 'ADMIN':
            # User is logged in but not an ADMIN role
            logout(request)
            if request.user.role == 'USER':
                return HttpResponseRedirect(reverse("login_page") + "?error=invalid_role")
            elif request.user.role == 'SERVICER':
                return HttpResponseRedirect(reverse("servicer_login") + "?error=invalid_role")
            else:
                return HttpResponseRedirect(reverse("admin_login") + "?error=invalid_role")
        
        return view_func(request, *args, **kwargs)
    return wrapper



from django.contrib.auth.decorators import login_required

def login_page(request):
    """
    Handle user login functionality.
    - Only allows USER role to log in
    - Validates credentials using Django authentication
    - Checks if account is active
    - Redirects to user home on success
    - Shows error messages for invalid credentials or inactive accounts
    """
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        # Check if user has USER role, if not, logout and show error
        if request.user.role == 'USER':
            return redirect("user_home")
        else:
            # User is logged in but not a USER role, logout them
            logout(request)
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
        # Validate empty fields
        if not username:
            return HttpResponseRedirect(reverse("login_page") + "?error=empty_username")
        if not password:
            return HttpResponseRedirect(reverse("login_page") + "?error=empty_password")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                return HttpResponseRedirect(reverse("login_page") + "?error=inactive")
            
            # Check if user has USER role
            if user.role != 'USER':
                return HttpResponseRedirect(reverse("login_page") + "?error=invalid_role")
            
            # Login successful - create session
            login(request, user)
            return redirect("user_home")
        else:
            # Invalid credentials
            return HttpResponseRedirect(reverse("login_page") + "?error=invalid")

    return render(request, "accounts/login.html")


def user_register(request):
    """
    Handle user registration with comprehensive validation.
    - Validates all fields according to requirements
    - Shows specific error messages for each validation failure
    - Only saves user if all validations pass
    - Password is automatically hashed by Django
    - Redirects to login page on success
    """
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                # Save user (password is automatically hashed by UserCreationForm)
                user = form.save()
                
                # Verify user was created successfully
                if user and user.pk:
                    # Redirect to login page with success parameter
                    return HttpResponseRedirect(reverse("login_page") + "?registered=success")
                else:
                    return HttpResponseRedirect(reverse("user_register") + "?error=failed")
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Registration error: {str(e)}")
                return HttpResponseRedirect(reverse("user_register") + "?error=exception")
        else:
            # Form has validation errors - render with form errors
            pass
    else:
        # GET request - show empty form
        form = UserRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
@user_role_required
def user_home(request):
    user_name = request.user.first_name or request.user.username
    services = ["Oil Change", "Tire Rotation", "Brake Inspection"]

    # Fetch latest work progress for logged-in user through booking relationship
    work_list = WorkProgress.objects.filter(booking__user=request.user).order_by("-updated_at")[:6]

    # Feedback via modal popup
    if request.method == "POST":
        message = request.POST.get("feedback_message")
        if message:
            Feedback.objects.create(user=request.user, message=message)
            messages.success(request, "Feedback submitted successfully!")
            return redirect("user_home")

    return render(request, "user_home.html", {
        "user_name": user_name,
        "services": services,
        "work_list": work_list,
    })

@login_required
@user_role_required
def user_search(request):
    query = request.GET.get("q", "")
    work_type = request.GET.get("type", "")
    location = request.GET.get("location", "")

    servicers = Servicer.objects.all()

    if query:
        servicers = servicers.filter(
            name__icontains=query
        ) | servicers.filter(
            work_type__icontains=query
        )

    if work_type:
        servicers = servicers.filter(work_type=work_type)

    if location:
        servicers = servicers.filter(location__icontains=location)

    work_types = Servicer.objects.values_list("work_type", flat=True).distinct()
    locations = Servicer.objects.values_list("location", flat=True).distinct()

    return render(request, "user_search.html", {
        "servicers": servicers,
        "work_types": work_types,
        "locations": locations,
        "query": query,
        "selected_type": work_type,
        "selected_location": location,
    })

@login_required
@user_role_required
def user_work_status(request):
    """
    User Work Status page.
    Shows all bookings created by the logged-in user.
    Each booking shows: Service ID, Service center name, Work type, Status badge, View Details button.
    """
    # Get all bookings for the logged-in user, ordered by most recent first
    bookings = Booking.objects.filter(user=request.user).order_by("-created_at")

    # Prepare complaints list for each booking
    for b in bookings:
        if b.complaints:
            b.complaint_list = b.complaints.split(" || ")
        else:
            b.complaint_list = []

    return render(request, "user_work_status.html", {
        "bookings": bookings
    })
    
@login_required
@user_role_required
def booking_detail(request, booking_id):
    """
    Booking Detail page for users.
    Shows booking details with conditional tabs:
    - Service Log (always visible)
    - Diagnostics (ONLY if status == "Pending" AND diagnosis exists)
    """
    # Get booking - ensure it belongs to the logged-in user
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Work progress timeline - ordered by updated_at (most recent first)
    # Get progress updates in chronological order (oldest first for timeline)
    progress = WorkProgress.objects.filter(booking=booking).order_by("updated_at")

    complaint_list = booking.complaints.split(" || ") if booking.complaints else []

    # Check if diagnosis exists and is visible
    # Diagnosis is visible ONLY when:
    # 1. Booking status is "Pending"
    # 2. Diagnosis exists
    diagnosis_visible = False
    diagnosis = None
    if booking.status == "Pending":
        try:
            diagnosis = booking.diagnosis
            diagnosis_visible = True
        except Diagnosis.DoesNotExist:
            diagnosis_visible = False

    return render(request, "booking_detail.html", {
        "booking": booking,
        "progress": progress,
        "complaint_list": complaint_list,
        "diagnosis": diagnosis,
        "diagnosis_visible": diagnosis_visible,
    })




@login_required
@user_role_required
@login_required
@user_role_required
def user_payment(request):
    """
    User Payment page.
    Displays list of pending payment requests for the logged-in user.
    Shows bookings where:
    - booking.user == logged-in user
    - booking.status == "Completed"
    - booking.payment_status == "Pending"
    """
    # Get pending payment requests for the user
    pending_payments = Booking.objects.filter(
        user=request.user,
        status='Completed',
        payment_status='Pending',
        payment_requested=True
    ).order_by('-created_at')
    
    return render(request, "user_payment.html", {
        'pending_payments': pending_payments,
    })


@login_required
@user_role_required
def process_payment(request, booking_id):
    """
    Process payment for a booking.
    
    Preconditions:
    - User is authenticated (enforced by decorators)
    - Booking belongs to logged-in user
    - booking.status == "Completed"
    - booking.payment_status == "Pending"
    
    On confirm:
    - Update booking.payment_status → "Paid"
    - Record payment_date timestamp
    - Redirect to Work History
    - Show success message
    """
    # Validate booking belongs to user
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Precondition: Only allow payment for Completed bookings with Pending payment
    if booking.status != 'Completed':
        messages.error(request, f"Cannot process payment. Booking status must be Completed. Current status: {booking.get_status_display()}")
        return redirect("user_payment")
    
    if booking.payment_status != 'Pending':
        if booking.payment_status == 'Paid':
            messages.warning(request, "This payment has already been processed.")
            return redirect("user_work_history")
        else:
            messages.error(request, "Payment status is invalid.")
            return redirect("user_payment")
    
    if request.method == "POST":
        # Double-check status hasn't changed (race condition protection)
        booking.refresh_from_db()
        if booking.payment_status != 'Pending':
            messages.error(request, "Payment status has changed. Cannot process payment.")
            return redirect("user_payment")
        
        # Update payment status to Paid
        from django.utils import timezone
        booking.payment_status = "Paid"
        booking.payment_date = timezone.now()
        booking.save()
        
        messages.success(request, f"Payment of ₹{booking.final_amount} processed successfully!")
        return redirect("user_work_history")
    
    # GET request - show confirmation page
    return render(request, "payment_confirmation.html", {
        'booking': booking,
    })


@login_required
@user_role_required
def user_work_history(request):
    """
    User Work History page.
    Shows completed bookings where:
    - booking.user == logged-in user
    - booking.status == "Completed"
    - booking.payment_status == "Paid"
    """
    # Get completed and paid bookings for the user
    completed_bookings = Booking.objects.filter(
        user=request.user,
        status='Completed',
        payment_status='Paid'
    ).order_by('-payment_date', '-created_at')
    
    return render(request, "work_history.html", {
        'completed_bookings': completed_bookings,
    })

@login_required
@user_role_required
def user_profile(request):
    """
    Handle user profile viewing and editing.
    - Display user profile information
    - Allow editing of first_name, last_name, email, phone
    - Handle password change
    """
    user = request.user
    profile_form = ProfileUpdateForm(instance=user, user=user)
    password_form = PasswordChangeForm(user=user)
    profile_success = False
    password_success = False
    
    if request.method == "POST":
        # Check which form was submitted
        if 'update_profile' in request.POST:
            profile_form = ProfileUpdateForm(request.POST, instance=user, user=user)
            if profile_form.is_valid():
                saved_user = profile_form.save()
                # Refresh user object from database to get updated data
                user.refresh_from_db()
                profile_success = True
                # Re-instantiate form with updated data
                profile_form = ProfileUpdateForm(instance=user, user=user)
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.POST, user=user)
            if password_form.is_valid():
                password_form.save()
                password_success = True
                # Re-instantiate form
                password_form = PasswordChangeForm(user=user)
                # Update session to keep user logged in after password change
                update_session_auth_hash(request, user)
    
    return render(request, "user_profile.html", {
        'user': user,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_success': profile_success,
        'password_success': password_success,
    })


@login_required
@user_role_required
def book_service(request, servicer_id):
    servicer = Servicer.objects.get(id=servicer_id)
    work_types = [w.strip() for w in servicer.work_type.split(",")]

    session_data = request.session.get("booking_data")
    fuel_types = ["Petrol", "Diesel", "Electric", "Hybrid"]

    if request.method == "POST":
        # Save/update session data
        request.session["booking_data"] = {
            "servicer_id": servicer.id,
            "vehicle_make": request.POST.get("vehicle_make"),
            "vehicle_model": request.POST.get("vehicle_model"),
            "owner_name": request.POST.get("owner_name"),
            "fuel_type": request.POST.get("fuel_type"),
            "year": request.POST.get("year"),
            "vehicle_number": request.POST.get("vehicle_number"),
            "work_type": request.POST.get("work_type"),
            "preferred_date": request.POST.get("preferred_date"),
            "complaints": request.POST.get("complaints"),
        }
        return redirect("booking_confirm")

    return render(request, "book_service.html", {
        "servicer": servicer,
        "work_types": work_types,
        "fuel_types": fuel_types,
        "data": session_data,
    })
@login_required
@user_role_required
def booking_confirm(request):
    data = request.session.get("booking_data")
    if not data:
        return redirect("user_search")

    servicer = Servicer.objects.get(id=data["servicer_id"])

    if request.method == "POST":
        Booking.objects.create(
            user=request.user,
            servicer=servicer,
            vehicle_make=data["vehicle_make"],
            vehicle_model=data["vehicle_model"],
            owner_name=data["owner_name"],
            fuel_type=data["fuel_type"],
            year=data["year"],
            vehicle_number=data["vehicle_number"],
            work_type=data["work_type"],
            preferred_date=data["preferred_date"],
            complaints=data["complaints"],
            status="Requested"
        )

        # 🔥 Clear session only AFTER saving
        del request.session["booking_data"]

        messages.success(request, "Service request sent successfully!")
        return redirect("user_work_status")

    return render(request, "booking_confirm.html", {
        "data": data,
        "servicer": servicer,
        "complaint_list": data["complaints"].split(" || ")
    })


@login_required
@user_role_required
def approve_diagnosis(request, booking_id):
    """
    Approve diagnosis and move booking to Ongoing status.
    
    Validation:
    - Booking must belong to the logged-in user
    - Status must be "Pending"
    - Diagnosis must exist
    - Diagnosis must not already be approved
    
    On success:
    - booking.status → "Ongoing"
    - diagnosis.user_approved → True
    - Redirect to booking detail with success message
    """
    # Get booking - ensure it belongs to the logged-in user
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Validate booking status
    if booking.status != "Pending":
        messages.error(request, "Diagnosis can only be approved when booking status is Pending.")
        return redirect("booking_detail", booking_id=booking_id)
    
    # Validate diagnosis exists
    try:
        diagnosis = booking.diagnosis
    except Diagnosis.DoesNotExist:
        messages.error(request, "Diagnosis report not found.")
        return redirect("booking_detail", booking_id=booking_id)
    
    # Prevent double approval
    if diagnosis.user_approved:
        messages.warning(request, "Diagnosis has already been approved.")
        return redirect("booking_detail", booking_id=booking_id)
    
    # Only allow POST requests
    if request.method == "POST":
        # Update booking status to Ongoing
        booking.status = "Ongoing"
        booking.save()
        
        # Mark diagnosis as approved
        diagnosis.user_approved = True
        diagnosis.save()
        
        messages.success(request, "Diagnosis approved successfully! Work has started.")
        return redirect("booking_detail", booking_id=booking_id)
    
    # If GET request, redirect to booking detail
    return redirect("booking_detail", booking_id=booking_id)


def user_logout(request):
    """
    Handle user logout functionality.
    - Logs out the current user
    - Clears session data
    - Redirects to login page
    """
    if request.user.is_authenticated:
        # Logout the user (clears authentication)
        logout(request)
        
        # Clear session data
        request.session.flush()
    
    # Redirect to login page
    return redirect('login_page')


# ==================== SERVICER AUTHENTICATION ====================

def servicer_login(request):
    """
    Handle servicer login functionality.
    - Only allows SERVICER role to log in
    - Validates credentials using Django authentication
    - Checks if account is active
    - Redirects to servicer home on success
    - Shows error messages for invalid credentials or inactive accounts
    """
    # If servicer is already logged in, redirect to home
    if request.user.is_authenticated:
        # Check if user has SERVICER role, if not, logout and show error
        if request.user.role == 'SERVICER':
            return redirect("servicer_home")
        else:
            # User is logged in but not a SERVICER role, logout them
            logout(request)
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
        # Validate empty fields
        if not username:
            return HttpResponseRedirect(reverse("servicer_login") + "?error=empty_username")
        if not password:
            return HttpResponseRedirect(reverse("servicer_login") + "?error=empty_password")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                return HttpResponseRedirect(reverse("servicer_login") + "?error=inactive")
            
            # Check if user has SERVICER role
            if user.role != 'SERVICER':
                return HttpResponseRedirect(reverse("servicer_login") + "?error=invalid_role")
            
            # Login successful - create session
            login(request, user)
            return redirect("servicer_home")
        else:
            # Invalid credentials
            return HttpResponseRedirect(reverse("servicer_login") + "?error=invalid")

    return render(request, "accounts/servicer_login.html")


def servicer_register(request):
    """
    Handle servicer registration with comprehensive validation.
    - Validates all fields according to requirements
    - Shows specific error messages for each validation failure
    - Only saves servicer if all validations pass
    - Password is automatically hashed by Django
    - Automatically assigns SERVICER role
    - Redirects to servicer login page on success
    """
    if request.method == "POST":
        form = ServicerRegisterForm(request.POST)
        if form.is_valid():
            try:
                # Save servicer (password is automatically hashed by UserCreationForm)
                user = form.save()
                
                # Verify servicer was created successfully
                if user and user.pk:
                    # Redirect to servicer login page with success parameter
                    return HttpResponseRedirect(reverse("servicer_login") + "?registered=success")
                else:
                    return HttpResponseRedirect(reverse("servicer_register") + "?error=failed")
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Servicer registration error: {str(e)}")
                return HttpResponseRedirect(reverse("servicer_register") + "?error=exception")
        else:
            # Form has validation errors - render with form errors
            pass
    else:
        # GET request - show empty form
        form = ServicerRegisterForm()

    return render(request, "accounts/servicer_register.html", {"form": form})


@login_required
@servicer_role_required
def servicer_home(request):
    """
    Servicer dashboard/home page.
    Shows summary cards and recent feedback.
    - Only accessible to logged-in servicers
    - Shows summary statistics
    - Shows recent feedback list
    """
    # Get servicer associated with logged-in user (match by email)
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found. Please contact support.")
        return redirect("servicer_login")
    
    # Get booking statistics
    total_requests = Booking.objects.filter(servicer=servicer, status='Requested').count()
    pending_requests = Booking.objects.filter(servicer=servicer, status='Pending').count()
    ongoing_works = Booking.objects.filter(servicer=servicer, status='Ongoing').count()
    completed_works = Booking.objects.filter(servicer=servicer, status='Completed').count()
    
    # Get recent feedback (limit to 5 most recent)
    recent_feedback = Feedback.objects.filter(
        user__in=Booking.objects.filter(servicer=servicer).values_list('user', flat=True)
    ).order_by('-created_at')[:5]
    
    servicer_name = request.user.first_name or request.user.username
    
    return render(request, "servicer_home.html", {
        "servicer_name": servicer_name,
        "servicer": servicer,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "ongoing_works": ongoing_works,
        "completed_works": completed_works,
        "recent_feedback": recent_feedback,
    })


def servicer_logout(request):
    """
    Handle servicer logout functionality.
    - Logs out the current servicer
    - Clears session data
    - Redirects to servicer login page
    """
    if request.user.is_authenticated:
        # Logout the servicer (clears authentication)
        logout(request)
        
        # Clear session data
        request.session.flush()
    
    # Redirect to servicer login page
    return redirect('servicer_login')


@login_required
@servicer_role_required
def servicer_worklist(request):
    """
    Servicer worklist page with tabs for different work states.
    Shows bookings filtered by status: Requested, Pending, Ongoing, Completed
    """
    # Get servicer associated with logged-in user (match by email)
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        # If no servicer found, create one or show error
        messages.error(request, "Servicer profile not found. Please contact support.")
        return redirect("servicer_home")
    
    # Get tab parameter (default to 'requested')
    tab = request.GET.get('tab', 'requested')
    
    # Filter bookings by status
    if tab == 'requested':
        bookings = Booking.objects.filter(servicer=servicer, status='Requested').order_by('-created_at')
    elif tab == 'pending':
        bookings = Booking.objects.filter(servicer=servicer, status='Pending').order_by('-created_at')
    elif tab == 'ongoing':
        bookings = Booking.objects.filter(servicer=servicer, status='Ongoing').order_by('-created_at')
    elif tab == 'completed':
        bookings = Booking.objects.filter(servicer=servicer, status='Completed').order_by('-created_at')
    else:
        bookings = Booking.objects.filter(servicer=servicer, status='Requested').order_by('-created_at')
        tab = 'requested'
    
    return render(request, "servicer_worklist.html", {
        'bookings': bookings,
        'active_tab': tab,
        'servicer': servicer,
    })


@login_required
@servicer_role_required
def servicer_booking_detail(request, booking_id):
    """
    Show detailed view of a booking for servicer.
    Different views based on booking status.
    """
    # Get servicer associated with logged-in user
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found.")
        return redirect("servicer_worklist")
    
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Get complaint list
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    # Get diagnosis if exists
    diagnosis = None
    if hasattr(booking, 'diagnosis'):
        diagnosis = booking.diagnosis
    
    # Get progress updates if exists
    progress_updates = WorkProgress.objects.filter(booking=booking).order_by('updated_at')
    
    context = {
        'booking': booking,
        'complaint_list': complaint_list,
        'diagnosis': diagnosis,
        'progress_updates': progress_updates,
    }
    
    return render(request, "servicer_booking_detail.html", context)


@login_required
@servicer_role_required
def accept_booking(request, booking_id):
    """
    Accept a booking request.
    Moves status from Requested to Pending (not Accepted).
    Requires pickup choice.
    Logs action in WorkProgress.
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found.")
        return redirect("servicer_worklist")
    
    # Validate booking belongs to this servicer and is in Requested status
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Prevent accepting already accepted/rejected bookings
    if booking.status != 'Requested':
        messages.error(request, f"Cannot accept booking. Current status: {booking.get_status_display()}")
        return redirect("servicer_worklist?tab=requested")
    
    if request.method == "POST":
        form = AcceptBookingForm(request.POST)
        if form.is_valid():
            # Update booking status to Pending (not Accepted)
            booking.status = 'Pending'
            booking.pickup_choice = form.cleaned_data['pickup_choice']
            booking.save()
            
            # Log action in WorkProgress
            WorkProgress.objects.create(
                booking=booking,
                title="Request Accepted",
                description=f"Service request accepted. Vehicle delivery: {booking.get_pickup_choice_display()}",
                status="Pending"
            )
            
            messages.success(request, "Booking accepted successfully! Please create diagnosis.")
            # Redirect to diagnosis creation page
            return redirect("create_diagnosis", booking_id=booking.id)
    else:
        form = AcceptBookingForm()
    
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    return render(request, "servicer_accept_booking.html", {
        'booking': booking,
        'form': form,
        'complaint_list': complaint_list,
    })


@login_required
@servicer_role_required
def reject_booking(request, booking_id):
    """
    Reject a booking request with a reason.
    Moves status to Rejected and stores reason.
    Logs action in WorkProgress.
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found.")
        return redirect("servicer_worklist")
    
    # Validate booking belongs to this servicer
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Prevent rejecting already accepted/rejected bookings
    if booking.status != 'Requested':
        messages.error(request, f"Cannot reject booking. Current status: {booking.get_status_display()}")
        return redirect("servicer_worklist?tab=requested")
    
    if request.method == "POST":
        form = RejectBookingForm(request.POST)
        if form.is_valid():
            # Update booking status to Rejected
            booking.status = 'Rejected'
            booking.rejection_reason = form.cleaned_data['reason']
            booking.save()
            
            # Log action in WorkProgress
            WorkProgress.objects.create(
                booking=booking,
                title="Request Rejected",
                description=f"Service request rejected. Reason: {booking.rejection_reason}",
                status="Pending"
            )
            
            messages.success(request, "Booking rejected.")
            return redirect("servicer_worklist?tab=requested")
    else:
        form = RejectBookingForm()
    
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    return render(request, "servicer_reject_booking.html", {
        'booking': booking,
        'form': form,
        'complaint_list': complaint_list,
    })


@login_required
@servicer_role_required
def create_diagnosis(request, booking_id):
    """
    Create diagnosis for a booking.
    
    Preconditions:
    - Servicer is authenticated (enforced by decorators)
    - Booking belongs to this servicer
    - booking.status == "Pending"
    - Diagnosis does NOT already exist
    
    On submit:
    - Create Diagnosis record linked to booking
    - Keep booking.status as "Pending" (user must approve)
    - Log action in WorkProgress
    - Redirect to Servicer Worklist
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found. Please contact support.")
        return redirect("servicer_worklist")
    
    # Validate booking belongs to servicer
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Precondition: Only allow diagnosis creation for Pending bookings
    if booking.status != 'Pending':
        messages.error(request, f"Cannot create diagnosis. Booking status must be Pending. Current status: {booking.get_status_display()}")
        return redirect("servicer_worklist?tab=pending")
    
    # Precondition: Prevent duplicate diagnosis
    if hasattr(booking, 'diagnosis'):
        messages.warning(request, "Diagnosis already exists for this booking. You cannot create another diagnosis.")
        return redirect("servicer_booking_detail", booking_id=booking.id)
    
    if request.method == "POST":
        form = DiagnosisForm(request.POST)
        if form.is_valid():
            # Double-check diagnosis doesn't exist (race condition protection)
            if hasattr(booking, 'diagnosis'):
                messages.warning(request, "Diagnosis already exists for this booking.")
                return redirect("servicer_booking_detail", booking_id=booking.id)
            
            # Create diagnosis
            diagnosis = form.save(commit=False)
            diagnosis.booking = booking
            diagnosis.save()
            
            # Log diagnosis creation in WorkProgress
            WorkProgress.objects.create(
                booking=booking,
                title="Diagnosis Submitted",
                description=f"Diagnosis report submitted. Estimated cost: ₹{diagnosis.estimated_cost if diagnosis.estimated_cost else 'Not specified'}. Waiting for user approval.",
                status="Pending"
            )
            
            # Status remains Pending (user must approve to move to Ongoing)
            # No need to update booking.status - it's already Pending
            
            messages.success(request, "Diagnosis submitted successfully! Waiting for user approval.")
            return redirect("servicer_worklist?tab=pending")
    else:
        form = DiagnosisForm()
    
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    return render(request, "servicer_create_diagnosis.html", {
        'booking': booking,
        'form': form,
        'complaint_list': complaint_list,
    })


@login_required
@servicer_role_required
def add_progress_update(request, booking_id):
    """
    Add a progress update for ongoing work.
    
    Preconditions:
    - Servicer is authenticated (enforced by decorators)
    - Booking belongs to this servicer
    - booking.status == "Ongoing"
    - Diagnosis exists and has been approved by user (user_approved == True)
    
    On submit:
    - Create WorkProgress entry linked to booking
    - Set WorkProgress.status = "In Progress" (automatically)
    - Do NOT change booking.status (remains "Ongoing")
    - Record updated_at timestamp (auto_now=True)
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found. Please contact support.")
        return redirect("servicer_worklist")
    
    # Validate booking belongs to servicer
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Precondition: Only allow progress updates for Ongoing bookings
    if booking.status != 'Ongoing':
        messages.error(request, f"Cannot add progress update. Booking status must be Ongoing. Current status: {booking.get_status_display()}")
        return redirect("servicer_worklist?tab=ongoing")
    
    # Precondition: Diagnosis must exist and be approved by user
    if not hasattr(booking, 'diagnosis'):
        messages.error(request, "Cannot add progress update. Diagnosis must be submitted and approved first.")
        return redirect("servicer_booking_detail", booking_id=booking.id)
    
    diagnosis = booking.diagnosis
    if not diagnosis.user_approved:
        messages.error(request, "Cannot add progress update. Diagnosis must be approved by the user first.")
        return redirect("servicer_booking_detail", booking_id=booking.id)
    
    if request.method == "POST":
        form = ProgressUpdateForm(request.POST)
        if form.is_valid():
            # Double-check status hasn't changed (race condition protection)
            booking.refresh_from_db()
            if booking.status != 'Ongoing':
                messages.error(request, "Booking status has changed. Cannot add progress update.")
                return redirect("servicer_booking_detail", booking_id=booking.id)
            
            # Create progress update
            progress = form.save(commit=False)
            progress.booking = booking
            # Set status automatically to "In Progress"
            progress.status = "In Progress"
            progress.save()
            
            messages.success(request, "Progress update added successfully!")
            return redirect("servicer_booking_detail", booking_id=booking_id)
    else:
        form = ProgressUpdateForm()
    
    # Get complaint list for display
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    return render(request, "servicer_add_progress.html", {
        'booking': booking,
        'form': form,
        'complaint_list': complaint_list,
    })


@login_required
@servicer_role_required
def mark_work_completed(request, booking_id):
    """
    Mark work as completed and request payment.
    
    Preconditions:
    - Servicer is authenticated (enforced by decorators)
    - Booking belongs to this servicer
    - booking.status == "Ongoing"
    - At least one WorkProgress entry exists
    
    On submit:
    - Update booking.status → "Completed"
    - Create WorkProgress entry: "Service Completed"
    - Set payment_requested = True
    - Set final_amount (from form or diagnosis estimate)
    - Save completion_notes (optional)
    - Redirect to servicer worklist
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found. Please contact support.")
        return redirect("servicer_worklist")
    
    # Validate booking belongs to servicer
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer)
    
    # Precondition: Only allow completion for Ongoing bookings
    if booking.status != 'Ongoing':
        messages.error(request, f"Cannot mark as completed. Booking status must be Ongoing. Current status: {booking.get_status_display()}")
        return redirect("servicer_worklist?tab=ongoing")
    
    # Precondition: At least one WorkProgress entry must exist
    progress_count = WorkProgress.objects.filter(booking=booking).count()
    if progress_count == 0:
        messages.error(request, "Cannot mark as completed. At least one progress update must be added first.")
        return redirect("servicer_booking_detail", booking_id=booking.id)
    
    # Precondition: Prevent re-completing an already completed booking
    if booking.status == 'Completed':
        messages.warning(request, "This booking is already marked as completed.")
        return redirect("servicer_booking_detail", booking_id=booking.id)
    
    # Get diagnosis to pre-fill estimated cost if available
    diagnosis = None
    estimated_cost = None
    if hasattr(booking, 'diagnosis'):
        diagnosis = booking.diagnosis
        estimated_cost = diagnosis.estimated_cost
    
    if request.method == "POST":
        form = CompleteWorkForm(request.POST, initial={'final_amount': estimated_cost})
        if form.is_valid():
            # Double-check status hasn't changed (race condition protection)
            booking.refresh_from_db()
            if booking.status != 'Ongoing':
                messages.error(request, "Booking status has changed. Cannot mark as completed.")
                return redirect("servicer_booking_detail", booking_id=booking.id)
            
            # Update booking status to Completed
            booking.status = 'Completed'
            booking.completion_notes = form.cleaned_data.get('completion_notes', '')
            booking.final_amount = form.cleaned_data['final_amount']
            # Set payment_requested = True and payment_status = "Pending" (payment is requested during completion)
            booking.payment_requested = True
            booking.payment_status = "Pending"
            booking.save()
            
            # Create WorkProgress entry for completion
            completion_description = form.cleaned_data.get('completion_notes', '')
            if not completion_description:
                completion_description = f"Service completed. Final amount: ₹{booking.final_amount}"
            else:
                completion_description = f"{completion_description} (Final amount: ₹{booking.final_amount})"
            
            WorkProgress.objects.create(
                booking=booking,
                title="Service Completed",
                description=completion_description,
                status="Completed"
            )
            
            messages.success(request, "Work marked as completed and payment request sent to user!")
            return redirect("servicer_worklist?tab=completed")
    else:
        # Pre-fill final_amount with diagnosis estimate if available
        form = CompleteWorkForm(initial={'final_amount': estimated_cost})
    
    # Get complaint list for display
    complaint_list = booking.complaints.split(" || ") if booking.complaints else []
    
    return render(request, "servicer_complete_work.html", {
        'booking': booking,
        'form': form,
        'complaint_list': complaint_list,
        'diagnosis': diagnosis,
    })


@login_required
@servicer_role_required
def request_payment(request, booking_id):
    """
    Request payment for completed work.
    Sets payment_requested flag.
    """
    # Get servicer
    try:
        servicer = Servicer.objects.get(email=request.user.email)
    except Servicer.DoesNotExist:
        messages.error(request, "Servicer profile not found.")
        return redirect("servicer_worklist")
    
    booking = get_object_or_404(Booking, id=booking_id, servicer=servicer, status='Completed')
    
    if request.method == "POST":
        booking.payment_requested = True
        booking.save()
        messages.success(request, "Payment request sent to user!")
        return redirect("servicer_booking_detail", booking_id=booking_id)
    
    return redirect("servicer_booking_detail", booking_id=booking_id)


@login_required
@servicer_role_required
def servicer_profile(request):
    """
    Handle servicer profile viewing and editing.
    - Display servicer profile information
    - Allow editing of personal info and servicer-specific fields
    - Handle password change
    """
    user = request.user
    profile_form = ServicerProfileUpdateForm(instance=user, user=user)
    password_form = PasswordChangeForm(user=user)
    profile_success = False
    password_success = False
    
    if request.method == "POST":
        # Check which form was submitted
        if 'update_profile' in request.POST:
            profile_form = ServicerProfileUpdateForm(request.POST, instance=user, user=user)
            if profile_form.is_valid():
                saved_user = profile_form.save()
                # Refresh user object from database to get updated data
                user.refresh_from_db()
                profile_success = True
                # Re-instantiate form with updated data
                profile_form = ServicerProfileUpdateForm(instance=user, user=user)
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.POST, user=user)
            if password_form.is_valid():
                password_form.save()
                password_success = True
                # Re-instantiate form
                password_form = PasswordChangeForm(user=user)
                # Update session to keep user logged in after password change
                update_session_auth_hash(request, user)
    
    return render(request, "servicer_profile.html", {
        'user': user,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_success': profile_success,
        'password_success': password_success,
    })


# ==================== ADMIN AUTHENTICATION ====================

def admin_login(request):
    """
    Handle admin login functionality.
    - Only allows ADMIN role to log in
    - Validates credentials using Django authentication
    - Checks if account is active
    - Redirects to admin home on success
    - Shows error messages for invalid credentials or inactive accounts
    - NO registration option (admins must be created manually)
    """
    # If admin is already logged in, redirect to home
    if request.user.is_authenticated:
        # Check if user has ADMIN role, if not, logout and show error
        if request.user.role == 'ADMIN':
            return redirect("admin_home")
        else:
            # User is logged in but not an ADMIN role, logout them
            logout(request)
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        
        # Validate empty fields
        if not username:
            return HttpResponseRedirect(reverse("admin_login") + "?error=empty_username")
        if not password:
            return HttpResponseRedirect(reverse("admin_login") + "?error=empty_password")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                return HttpResponseRedirect(reverse("admin_login") + "?error=inactive")
            
            # Check if user has ADMIN role
            if user.role != 'ADMIN':
                return HttpResponseRedirect(reverse("admin_login") + "?error=invalid_role")
            
            # Login successful - create session
            login(request, user)
            return redirect("admin_home")
        else:
            # Invalid credentials
            return HttpResponseRedirect(reverse("admin_login") + "?error=invalid")

    return render(request, "accounts/admin_login.html")


@login_required
@admin_role_required
def admin_home(request):
    """
    Admin dashboard/home page (placeholder).
    - Only accessible to logged-in admins
    - Shows basic dashboard layout with sidebar
    - Placeholder for analytics, latest status, and feedback view
    """
    admin_name = request.user.username
    
    return render(request, "admin_home.html", {
        "admin_name": admin_name,
    })


@login_required
@admin_role_required
def admin_customers(request):
    """
    Admin page to list all customers (users with role=USER).
    Placeholder implementation.
    """
    from .models import User
    customers = User.objects.filter(role='USER')
    
    return render(request, "admin_customers.html", {
        "customers": customers,
    })


@login_required
@admin_role_required
def admin_servicers(request):
    """
    Admin page to list all servicers (users with role=SERVICER).
    Placeholder implementation.
    """
    from .models import User
    servicers = User.objects.filter(role='SERVICER')
    
    return render(request, "admin_servicers.html", {
        "servicers": servicers,
    })


@login_required
@admin_role_required
def admin_settings(request):
    """
    Admin settings page (placeholder).
    - Change landing page image (UI only)
    - Add admin users (UI only)
    - No functionality implemented yet
    """
    return render(request, "admin_settings.html")


def admin_logout(request):
    """
    Handle admin logout functionality.
    - Logs out the current admin
    - Clears session data
    - Redirects to admin login page
    """
    if request.user.is_authenticated:
        # Logout the admin (clears authentication)
        logout(request)
        
        # Clear session data
        request.session.flush()
    
    # Redirect to admin login page
    return redirect('admin_login')
