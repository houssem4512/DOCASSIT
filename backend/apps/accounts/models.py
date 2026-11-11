from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [("user", "User"), ("admin", "Admin")]
    role = models.CharField(max_length=10, choices=ROLES, default="user")
    language = models.CharField(max_length=2, default="en")
    email = models.EmailField(blank=True)
