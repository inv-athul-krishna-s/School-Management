
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser
import csv
from io import TextIOWrapper

from core.utils import CSVExportMixin

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
    # core/views.py  ── inside StudentViewSet  (put right after `me()`)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser],
        permission_classes=[permissions.IsAuthenticated, IsAdmin],
    )
    def import_csv(self, request):
        """
        Accepts *one* CSV file whose header matches the keys below.
        Creates users & students row‑by‑row; collects any per‑row errors.
        Response:
        {
            "created": [ {student‑json‑1}, … ],
            "errors":  ["Row 2: duplicate roll_number", …]
        }
        """
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "CSV file is required."}, status=400)

        reader = csv.DictReader(TextIOWrapper(file, encoding="utf-8"))
        created, errors = [], []

        for idx, row in enumerate(reader, start=2):          # start=2 → 1‑based incl. header
            try:
                teacher = None
                teacher_id = row.get("assigned_teacher_id")
                if teacher_id:
                    teacher = Teacher.objects.get(pk=int(teacher_id))

                # build nested payload that StudentSerializer expects
                payload = {
                    "user": {
                        "username":   row["username"],
                        "email":      row["email"],
                        "first_name": row["first_name"],
                        "last_name":  row["last_name"],
                        "password":   row.get("password") or f'{row["username"]}123',
                    },
                    "phone":            row["phone"],
                    "roll_number":      row["roll_number"],
                    "student_class":    row["student_class"],
                    "date_of_birth":    row["date_of_birth"],
                    "admission_date":   row["admission_date"],
                    "status":           row.get("status", "active"),
                    "assigned_teacher": teacher.pk if teacher else None,
                }

                ser = StudentSerializer(data=payload)
                ser.is_valid(raise_exception=True)
                created.append(ser.save())
            except Exception as exc:
                errors.append(f"Row {idx}: {exc}")

        out_ser = StudentSerializer(created, many=True)
        return Response({"created": out_ser.data, "errors": errors},
                        status=201 if created else 400)

    


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
        "id", "user__username", "user__email", "user__first_name", "user__last_name",
        "subject_specialization", "employee_id", "date_of_joining", "status"
    ]
    csv_headers = [
        "ID", "Username", "Email", "First Name", "Last Name",
        "Subject", "Employee ID", "Joined On", "Status"
    ]


class StudentExportView(CSVExportMixin, StudentViewSet):
    csv_filename = "students.csv"
    csv_fields = [
        "id", "user__username", "user__email", "user__first_name", "user__last_name",
        "roll_number", "student_class", "date_of_birth", "admission_date",
        "status", "assigned_teacher__user__username"
    ]
    csv_headers = [
        "ID", "Username", "Email", "First Name", "Last Name",
        "Roll Number", "Class", "Date of Birth", "Admission Date",
        "Status", "Assigned Teacher"
    ]

    from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg
from django.utils import timezone

from .models import Exam, StudentExam, Question, Option, Answer
from .serializers import (ExamReadSerializer, ExamCreateSerializer,
                          SubmitExamSerializer, StudentExamSerializer)
from .permission import (IsAdmin, IsTeacher, IsTeacherOwner,
                          IsStudentOfTeacher)


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.select_related('teacher').all()

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Exam.objects.select_related("teacher")
        if user.role == "teacher" and hasattr(user, "teacher"):
            return Exam.objects.filter(teacher=user.teacher)
        if user.role == "student" and hasattr(user, "student"):
            t = user.student.assigned_teacher
            return Exam.objects.filter(teacher=t) if t else Exam.objects.none()
        return Exam.objects.none()

    permission_classes = [IsAuthenticated]

    # ---------- serializers ----------
    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ExamCreateSerializer
        if self.action == 'results':
            return StudentExamSerializer
        return ExamReadSerializer

    # ---------- creation logic ----------
    def perform_create(self, serializer):
        """Teachers become owner automatically unless admin specifies one."""
        if hasattr(self.request.user, 'teacher') and not self.request.user.is_staff:
            serializer.save(teacher=self.request.user.teacher)
        else:
            serializer.save()

    # ---------- fine‑grained permissions ----------
    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            self.permission_classes = [IsAuthenticated & (IsAdmin | IsTeacherOwner)]
        elif self.action == 'create':
            self.permission_classes = [IsAuthenticated & (IsAdmin | IsTeacher)]
        elif self.action == 'results':
            self.permission_classes = [IsAuthenticated & (IsAdmin | IsTeacherOwner)]
        elif self.action == 'submit':
            self.permission_classes = [IsAuthenticated & IsStudentOfTeacher]
        else:  # list & retrieve
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    # ---------- student submits answers ----------
    @action(detail=True, methods=['POST'], serializer_class=SubmitExamSerializer)
    def submit(self, request, pk=None):
        exam = self.get_object()  # permission already checked
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attempt, _ = StudentExam.objects.get_or_create(
            student=request.user.student,
            exam=exam,
            defaults={'started_at': timezone.now()}
        )
        if attempt.finished_at:
            return Response({'detail': 'You already submitted.'},
                            status=status.HTTP_400_BAD_REQUEST)

        total, correct = 0, 0
        for ans in serializer.validated_data['answers']:
            total += 1
            try:
                question = Question.objects.get(pk=ans['question_id'], exam=exam)
                option   = Option.objects.get(pk=ans['option_id'], question=question)
            except (Question.DoesNotExist, Option.DoesNotExist):
                continue
            Answer.objects.create(attempt=attempt, question=question, chosen=option)
            if option.is_correct:
                correct += 1

        attempt.finished_at = timezone.now()
        attempt.score = (correct / total) * 100 if total else 0
        attempt.save()

        return Response({'score': attempt.score})

    # ---------- teacher/admin view results ----------
    @action(detail=True, methods=['GET'])
    def results(self, request, pk=None):
        exam = self.get_object()  # permission already checked
        qs   = exam.attempts.select_related('student__user')
        data = {
            'exam': exam.title,
            'average_score': qs.aggregate(avg=Avg('score'))['avg'],
            'attempts': StudentExamSerializer(qs, many=True).data
        }
        return Response(data)
