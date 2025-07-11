
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from school_mgmt.core.utils import CSVExportMixin

from .models import Teacher, Student
from .serializers import TeacherSerializer, StudentSerializer, CustomTokenObtainPairSerializer
from .permission import IsAdmin, IsTeacher, IsSelfReadOnly

class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer
    queryset = Teacher.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Teacher.objects.all()
        elif user.role == "teacher":
            return Teacher.objects.filter(user=user)
        return Teacher.objects.none()

    def get_permissions(self):
        user = self.request.user
        if user.role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        elif user.role == "teacher":
            if self.action in ["list", "retrieve"]:
                return [permissions.IsAuthenticated(), IsTeacher()]
        return [permissions.IsAuthenticated()]
    def create(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can create teacher."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can update teacher."}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can delete teacher."}, status=403)
        return super().destroy(request, *args, **kwargs)


    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        if request.user.role != "teacher":
            return Response({"detail": "Not allowed."}, status=403)
        teacher = Teacher.objects.filter(user=request.user).first()
        if teacher:
            return Response(self.get_serializer(teacher).data)
        return Response({"detail": "Teacher profile not found."}, status=404)

    @action(detail=True, methods=["get"], url_path="students")
    def students(self, request, pk=None):
        teacher = self.get_object()
        if request.user.role == "teacher" and teacher.user != request.user:
            return Response({"detail": "Not allowed."}, status=403)
        queryset = teacher.student_set.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(StudentSerializer(page, many=True).data)
        return Response(StudentSerializer(queryset, many=True).data)

class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Student.objects.all()
        elif user.role == "teacher":
            return Student.objects.filter(assigned_teacher__user=user)
        elif user.role == "student":
            return Student.objects.filter(user=user)
        return Student.objects.none()

    def get_permissions(self):
        user = self.request.user
        if user.role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        elif user.role == "teacher":
            if self.action in ["list", "retrieve", "update", "partial_update"]:
                return [permissions.IsAuthenticated(), IsTeacher()]
        elif user.role == "student":
            if self.action in ["retrieve", "me"]:
                return [permissions.IsAuthenticated(), IsSelfReadOnly()]
            elif self.action in ["create", "destroy", "update", "partial_update", "list"]:
                return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]
    def create(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can create students."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role == "student":
            return Response({"detail": "Students cannot update any record."}, status=403)
        if request.user.role == "teacher":
            instance = self.get_object()
            if instance.assigned_teacher.user != request.user:
                return Response({"detail": "Not your assigned student."}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can delete students."}, status=403)
        return super().destroy(request, *args, **kwargs)




    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        if request.user.role != "student":
            return Response({"detail": "Not allowed."}, status=403)
        student = Student.objects.filter(user=request.user).first()
        if student:
            return Response(self.get_serializer(student).data)
        return Response({"detail": "Student profile not found."}, status=404)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LogoutView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "Refresh token missing."}, status=400)
        try:
            RefreshToken(refresh).blacklist()
            return Response({"detail": "Logged out successfully."}, status=205)
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=400)


class TeacherExportView(CSVExportMixin, TeacherViewSet):
    csv_filename = "teachers.csv"
    csv_fields = [
        "id", "user__username", "subject_specialization",
        "employee_id", "date_of_joining", "status"
    ]


class StudentExportView(CSVExportMixin, StudentViewSet):
    csv_filename = "students.csv"
    csv_fields = [
        "id", "user__username", "roll_number",
        "student_class", "date_of_birth",
        "admission_date", "status", "assigned_teacher_id",
    ]
