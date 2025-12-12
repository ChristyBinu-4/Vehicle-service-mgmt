from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login_page'),
    path('register/', views.user_register, name='user_register'),
    path('home/', views.user_home, name="user_home"),
    path('search/', views.user_search, name="user_search"),
    path('work-status/', views.user_work_status, name="user_work_status"),
    path('payment/', views.user_payment, name="user_payment"),
    path('profile/', views.user_profile, name="user_profile"),
    path('logout/', views.user_logout, name='logout'), 
]