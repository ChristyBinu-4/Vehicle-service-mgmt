from django.urls import path
from . import views

urlpatterns = [
    # User authentication routes
    path('', views.login_page, name='login_page'),
    path('register/', views.user_register, name='user_register'),
    path('home/', views.user_home, name="user_home"),
    path('search/', views.user_search, name="user_search"),
    path('work-status/', views.user_work_status, name="user_work_status"),
    path('payment/', views.user_payment, name="user_payment"),
    path('payment/<int:booking_id>/process/', views.process_payment, name="process_payment"),
    path('work-history/', views.user_work_history, name="user_work_history"),
    path('profile/', views.user_profile, name="user_profile"),
    path('logout/', views.user_logout, name='logout'), 
    path("book-service/<int:servicer_id>/", views.book_service, name="book_service"),
    path("booking-confirm/", views.booking_confirm, name="booking_confirm"),
    path("booking/<int:booking_id>/", views.booking_detail, name="booking_detail"),
    path("booking/<int:booking_id>/approve-diagnosis/", views.approve_diagnosis, name="approve_diagnosis"),
    
    # Servicer authentication routes
    path('servicer/login/', views.servicer_login, name='servicer_login'),
    path('servicer/register/', views.servicer_register, name='servicer_register'),
    path('servicer/home/', views.servicer_home, name='servicer_home'),
    path('servicer/profile/', views.servicer_profile, name='servicer_profile'),
    path('servicer/logout/', views.servicer_logout, name='servicer_logout'),
    
    # Servicer work management routes
    path('servicer/worklist/', views.servicer_worklist, name='servicer_worklist'),
    path('servicer/booking/<int:booking_id>/', views.servicer_booking_detail, name='servicer_booking_detail'),
    path('servicer/booking/<int:booking_id>/accept/', views.accept_booking, name='accept_booking'),
    path('servicer/booking/<int:booking_id>/reject/', views.reject_booking, name='reject_booking'),
    path('servicer/booking/<int:booking_id>/diagnosis/', views.create_diagnosis, name='create_diagnosis'),
    path('servicer/booking/<int:booking_id>/progress/', views.add_progress_update, name='add_progress_update'),
    path('servicer/booking/<int:booking_id>/complete/', views.mark_work_completed, name='mark_work_completed'),
    path('servicer/booking/<int:booking_id>/request-payment/', views.request_payment, name='request_payment'),
    
    # Admin authentication routes
    path('monitor/login/', views.admin_login, name='admin_login'),
    path('monitor/home/', views.admin_home, name='admin_home'),
    path('monitor/customers/', views.admin_customers, name='admin_customers'),
    path('monitor/servicers/', views.admin_servicers, name='admin_servicers'),
    path('monitor/settings/', views.admin_settings, name='admin_settings'),
    path('monitor/logout/', views.admin_logout, name='admin_logout'),
]