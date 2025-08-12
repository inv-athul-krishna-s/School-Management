from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

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

    def deactivate(self):
        self.status = "inactive"
        self.user.is_active = False
        self.user.save()
        self.save()


    def __str__(self):
        return f"{self.user.get_full_name()} – {self.roll_number}"
    
    # -----  EXAM MODELS  -----
from django.conf import settings
from django.db import models

class Exam(models.Model):
    """Created by an admin or a teacher; taken by the teacher’s students."""
    title        = models.CharField(max_length=120)
    description  = models.TextField(blank=True)
    teacher      = models.ForeignKey('core.Teacher', on_delete=models.PROTECT,
                                     related_name='exams',null=True,blank=True)
    target_class = models.CharField(max_length=50) #added a specific class for the exam
    start_time   = models.DateTimeField()
    duration_min = models.PositiveIntegerField()
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.duration_min)


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE,
                             related_name='questions')
    text = models.TextField()

    def __str__(self):
        return f'{self.exam.title} – Q{self.pk}'


class Option(models.Model):
    question   = models.ForeignKey(Question, on_delete=models.CASCADE,
                                   related_name='options')
    text       = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)   # exactly one True / question


class StudentExam(models.Model):
    """A student’s single attempt at an exam."""
    STATUS_CHOICES = [
        ("attempted", "Attempted"),
        ("unattempted", "Unattempted")
    ]
    student     = models.ForeignKey('core.Student', on_delete=models.CASCADE,
                                    related_name='exam_attempts')
    exam        = models.ForeignKey(Exam, on_delete=models.CASCADE,
                                    related_name='attempts')
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score       = models.DecimalField(max_digits=5, decimal_places=2,
                                      null=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                    default="unattempted")

    class Meta:
        unique_together = ('student', 'exam')


class Answer(models.Model):
    attempt  = models.ForeignKey(StudentExam, on_delete=models.CASCADE,
                                 related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    chosen   = models.ForeignKey(Option, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('attempt', 'question')




class Chat(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chats")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_chats")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ("timestamp",)

    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}"
