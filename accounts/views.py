from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.http import HttpResponseRedirect
from functools import wraps

from .forms import UserRegisterForm, FeedbackForm
from .models import Feedback, WorkProgress, Servicer, Booking


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
    booking = Booking.objects.get(id=booking_id, user=request.user)

    # Work progress timeline
    progress = WorkProgress.objects.filter(booking=booking).order_by("updated_at")

    complaint_list = booking.complaints.split(" || ") if booking.complaints else []

    return render(request, "booking_detail.html", {
        "booking": booking,
        "progress": progress,
        "complaint_list": complaint_list,
    })




@login_required
@user_role_required
def user_payment(request):
    return render(request, "user_payment.html")

@login_required
@user_role_required
def user_profile(request):
    return render(request, "user_profile.html")


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
def diagnosis_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != "Pending":
        messages.error(request, "Diagnosis is not available yet.")
        return redirect("user_work_status")

    if not hasattr(booking, "diagnosis"):
        messages.error(request, "Diagnosis report not submitted yet.")
        return redirect("user_work_status")

    return render(request, "diagnosis_detail.html", {
        "booking": booking,
        "diagnosis": booking.diagnosis
    })


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
