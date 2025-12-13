from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .forms import UserRegisterForm, FeedbackForm
from .models import Feedback, WorkProgress, Servicer, Booking



from django.contrib.auth.decorators import login_required

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login Successful!")
            return redirect("user_home")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("login_page")

    return render(request, "accounts/login.html")


def user_register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! Please login.")
            return redirect("login_page")
        else:
            messages.error(request, "Registration failed. Please check details.")
    else:
        form = UserRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def user_home(request):
    user_name = request.user.first_name or request.user.username
    services = ["Oil Change", "Tire Rotation", "Brake Inspection"]

    # Fetch latest work progress for logged-in user
    work_list = WorkProgress.objects.filter(user=request.user).order_by("-updated_at")[:6]

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


def user_work_status(request):
    return render(request, "user_work_status.html")

def user_payment(request):
    return render(request, "user_payment.html")

def user_profile(request):
    return render(request, "user_profile.html")

@login_required
def book_service(request, servicer_id):
    servicer = Servicer.objects.get(id=servicer_id)

    if request.method == "POST":
        Booking.objects.create(
            user=request.user,
            servicer=servicer,
            vehicle_make=request.POST.get("vehicle_make"),
            vehicle_model=request.POST.get("vehicle_model"),
            owner_name=request.POST.get("owner_name"),
            fuel_type=request.POST.get("fuel_type"),
            year=request.POST.get("year"),
            vehicle_number=request.POST.get("vehicle_number"),
            vehicle_photo=request.FILES.get("vehicle_photo"),
            work_type=request.POST.get("work_type"),
            preferred_date=request.POST.get("preferred_date"),
            complaints=request.POST.get("complaints"),
        )
        messages.success(request, "Service request sent successfully!")
        return redirect("user_work_status")

    work_types = [w.strip() for w in servicer.work_type.split(",")]

    return render(request, "book_service.html", {
        "servicer": servicer,
        "work_types": work_types,
    })


def user_logout(request):
    logout(request)
    return redirect('login')
