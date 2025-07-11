from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    )
    role  = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Teacher(models.Model):
    user                  = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone                 = models.CharField(max_length=15)
    subject_specialization = models.CharField(max_length=100)
    employee_id           = models.CharField(max_length=20, unique=True)
    date_of_joining       = models.DateField()
    status                = models.CharField(max_length=10, choices=[("active", "Active"), ("inactive", "Inactive")])

    def __str__(self):
        return f"{self.user.get_full_name()} – {self.subject_specialization}"


class Student(models.Model):
    user             = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone            = models.CharField(max_length=15)
    roll_number      = models.CharField(max_length=20, unique=True)
    student_class    = models.CharField(max_length=50)
    date_of_birth    = models.DateField()
    admission_date   = models.DateField()
    status           = models.CharField(max_length=10, choices=[("active", "Active"), ("inactive", "Inactive")])
    assigned_teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

    def delete(self, *args, **kwargs):
        linked_user = self.user
        super().delete(*args, **kwargs)
        linked_user.delete()

    def __str__(self):
        return f"{self.user.get_full_name()} – {self.roll_number}"