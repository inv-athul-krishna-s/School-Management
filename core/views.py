from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Teacher, Student
from .serializers import TeacherSerializer, StudentSerializer

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return Student.objects.filter(assigned_teacher__user=user)
        return super().get_queryset()

