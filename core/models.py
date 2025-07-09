from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (('teacher', 'Teacher'), ('student', 'Student'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True)
    date_of_joining = models.DateField()
    status = models.CharField(max_length=10)

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    roll_number = models.CharField(max_length=50, unique=True)
    student_class = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    admission_date = models.DateField()
    status = models.CharField(max_length=10)
    assigned_teacher = models.ForeignKey(Teacher, null=True, on_delete=models.SET_NULL)

    