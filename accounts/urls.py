from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login_page'),
    path('register/', views.user_register, name='user_register'),
    path('home/', views.user_home, name='user_home'),
]
