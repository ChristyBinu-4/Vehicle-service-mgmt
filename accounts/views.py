from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm, FeedbackForm
from .models import WorkProgress, Feedback


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

def user_search(request):
    return render(request, "user_search.html")

def user_work_status(request):
    return render(request, "user_work_status.html")

def user_payment(request):
    return render(request, "user_payment.html")

def user_profile(request):
    return render(request, "user_profile.html")


def user_logout(request):
    logout(request)
    return redirect('login')
