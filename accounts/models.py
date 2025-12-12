from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('servicer', 'Servicer'),
        ('admin', 'Admin'),
    )
    
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username

class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Feedback"
      
class WorkProgress(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    work_type = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.work_type} - {self.status}"
