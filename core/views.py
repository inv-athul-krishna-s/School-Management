# core/views.py
from io import TextIOWrapper
import csv

from django.db.models import Avg
from django.utils import timezone
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import smart_bytes
from django.core.mail import send_mail
from rest_framework.permissions import AllowAny
from rest_framework import generics

from rest_framework.decorators import action

from .models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Exam, StudentExam
from .models import Chat
from .serializers import ChatSerializer
from .serializers import MessageSerializer

from core.utils import CSVExportMixin
from .models import (
    Teacher, Student,
    Exam, Question, Option, Answer, StudentExam
)
from .serializers import (
    TeacherSerializer, StudentSerializer, CustomTokenObtainPairSerializer,
    ExamCreateSerializer, ExamReadSerializer,
    SubmitExamSerializer, StudentExamSerializer
)
from .permission import (
    IsAdmin, IsTeacher, IsSelfReadOnly,
    IsTeacherOwner, IsStudentOfTeacher
)

# ─────────────────────────────────────────────
#  TEACHER VIEWSET
# ─────────────────────────────────────────────
class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer
    queryset = Teacher.objects.all()

    # ----- queryset filtering -----
    def get_queryset(self):
        u = self.request.user
        if u.role == "admin":
            return Teacher.objects.all()
        if u.role == "teacher":
            return Teacher.objects.filter(user=u)
        return Teacher.objects.none()
    #To view their teacher
    def retrieve(self, request, *args, **kwargs):
        instance = Teacher.objects.filter(pk=kwargs["pk"]).first()
        if not instance:
            return Response({"detail": "Not found."}, status=404)

    # Students can only read their own assigned teacher
        if request.user.role == "student":
            student = getattr(request.user, "student", None)
            if not student or student.assigned_teacher_id != instance.pk:
                return Response({"detail": "Not allowed."}, status=403)

    # Teachers can read self, admins can read all
        if request.user.role == "teacher" and instance.user != request.user:
            return Response({"detail": "Not allowed."}, status=403)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ----- permissions -----
    def get_permissions(self):
        u = self.request.user
        if u.role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if u.role == "teacher" and self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        return [permissions.IsAuthenticated()]

    # ----- CRUD protections -----
    def create(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can create teacher."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response({"detail": "Only admin can update teacher."}, status=403)
        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role != "admin":
            return Response({"detail": "Only admin can delete teacher."}, status=403)

        instance.status = "inactive"
        instance.save()
        instance.user.is_active = False
        instance.user.save()
        return Response({"detail": "Teacher set to inactive."}, status=200)


    # ----- custom endpoints -----
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
        qs = teacher.student_set.all()
        page = self.paginate_queryset(qs)
        ser = StudentSerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page else Response(ser.data)


# ─────────────────────────────────────────────
#  STUDENT VIEWSET
# ─────────────────────────────────────────────
class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all()

    # ----- queryset filtering -----
    def get_queryset(self):
        u = self.request.user
        if u.role == "admin":
            return Student.objects.all()
        if u.role == "teacher":
            return Student.objects.filter(assigned_teacher__user=u)
        if u.role == "student":
            return Student.objects.filter(user=u)
        return Student.objects.none()
    
    def get_serializer_context(self):
        return {"request": self.request}

    # ----- permissions -----
    def get_permissions(self):
        u = self.request.user
        if u.role == "admin":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if u.role == "teacher" and self.action in ["list", "retrieve", "update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsTeacher()]
        if u.role == "student":
            if self.action in ["retrieve", "me"]:
                return [permissions.IsAuthenticated(), IsSelfReadOnly()]
            if self.action in ["create", "destroy", "update", "partial_update", "list"]:
                return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    # ----- CRUD protections -----
    def create(self, request, *args, **kwargs):
        if request.user.role == "admin":
            return super().create(request, *args, **kwargs)
    
        if request.user.role == "teacher":
            data = request.data.copy()
            data["assigned_teacher"] = request.user.teacher.id  # Auto-assign to self

        # Parse nested user object
            user_data = data.get("user", {})
            if isinstance(user_data, str):  # In case it's passed as a string (JSON)
                import json
                user_data = json.loads(user_data)
                data["user"] = user_data

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=201)

        return Response({"detail": "Not allowed."}, status=403)

    def update(self, request, *args, **kwargs):
        if request.user.role == "student":
            return Response({"detail": "Students cannot update any record."}, status=403)
        if request.user.role == "teacher":
            if self.get_object().assigned_teacher.user != request.user:
                return Response({"detail": "Not your assigned student."}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Admins can soft delete any student; Teachers only their assigned students
        if request.user.role == "admin" or \
           (request.user.role == "teacher" and instance.assigned_teacher and instance.assigned_teacher.user == request.user):
            
            instance.status = "inactive"  # Soft delete
            instance.save()
            instance.user.is_active = False
            instance.user.save()
            return Response({"detail": "Student set to inactive."}, status=200)

        return Response({"detail": "Not allowed."}, status=403)


    # ----- Providing custom end points to get their own profile -----
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        if request.user.role != "student":
            return Response({"detail": "Not allowed."}, status=403)
        stu = Student.objects.filter(user=request.user).first()
        return Response(self.get_serializer(stu).data) if stu else Response({"detail": "Student profile not found."}, status=404)
    @action(detail=False, methods=["get"], url_path="results")
    def my_results(self, request):
        if request.user.role != "student":
            return Response({"detail": "Not allowed."}, status=403)

        student = getattr(request.user, "student", None)
        if not student:
            return Response({"detail": "Student profile not found."}, status=404)

        attempts = StudentExam.objects.filter(student=student).select_related("exam")
        data = [
            {
                "exam_title": attempt.exam.title,
                "score": attempt.score,
                "started_at": attempt.started_at,
                "finished_at": attempt.finished_at
            }
            for attempt in attempts
        ]
        return Response(data)

    @action(
        detail=False, methods=["post"], url_path="import",
        parser_classes=[MultiPartParser],
        permission_classes=[permissions.IsAuthenticated, IsAdmin],
    )
    def import_csv(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "CSV file is required."}, status=400)

        reader = csv.DictReader(TextIOWrapper(file, encoding="utf-8"))
        created, errors = [], []
        for idx, row in enumerate(reader, start=2):
            try:
                teacher = Teacher.objects.filter(pk=row.get("assigned_teacher_id")).first()
                payload = {
                    "user": {
                        "username": row["username"],
                        "email": row["email"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "password": row.get("password") or f'{row["username"]}123'
                    },
                    "phone": row["phone"],
                    "roll_number": row["roll_number"],
                    "student_class": row["student_class"],
                    "date_of_birth": row["date_of_birth"],
                    "admission_date": row["admission_date"],
                    "status": row.get("status", "active"),
                    "assigned_teacher": teacher.pk if teacher else None
                }
                ser = StudentSerializer(data=payload)
                ser.is_valid(raise_exception=True)
                created.append(ser.save())
            except Exception as exc:
                errors.append(f"Row {idx}: {exc}")

        return Response({"created": StudentSerializer(created, many=True).data, "errors": errors},
                        status=201 if created else 400)

#  AUTH VIEW(S)

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


# ─────────────────────────────────────────────
#  EXPORT VIEWSETS (CSV)
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  SINGLE, FEATURE‑COMPLETE EXAM VIEWSET
# ─────────────────────────────────────────────
class ExamViewSet(viewsets.ModelViewSet):
    """
    Admin      →sees all exams, can create and assign any teacher  
    Teacher    →sees & edits only own exams, auto-assigned on create  
    Student    →sees exams created by their assigned_teacher  and admin 
    """
    permission_classes = [IsAuthenticated]

    # ----- queryset per role -----
    def get_queryset(self):
        u = self.request.user

        if u.role == "admin":
            return Exam.objects.select_related("teacher").all()

        elif u.role == "teacher" and hasattr(u, "teacher"):
            return Exam.objects.filter(teacher=u.teacher)

        elif u.role == "student" and hasattr(u, "student"):
            assigned_teacher = u.student.assigned_teacher
            student_class = self.request.user.student.student_class
            base_class = ''.join(filter(str.isdigit, student_class))  # "10A" → "10"

        return Exam.objects.filter(target_class=base_class)


    # ----- serializer choice -----
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ExamCreateSerializer
        if self.action == "results":
            return StudentExamSerializer
        if self.action == "submit":
            return SubmitExamSerializer
        return ExamReadSerializer

    # ----- create -----
    def perform_create(self, serializer):
        u = self.request.user
        if u.role == "teacher":
            serializer.save(teacher=u.teacher)
        elif u.role == "admin":
            serializer.save()
        else:
            raise PermissionDenied("Only admins and teachers can create exams.")

    # ----- permissions per action -----
    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), (IsAdmin() if self.request.user.role == "admin" else IsTeacherOwner())]
        if self.action == "create":
            return [IsAuthenticated(), (IsAdmin() if self.request.user.role == "admin" else IsTeacher())]
        if self.action == "results":
            return [IsAuthenticated(), (IsAdmin() if self.request.user.role == "admin" else IsTeacherOwner())]
        if self.action == "submit":
            return [IsAuthenticated(), IsStudentOfTeacher()]
        return [IsAuthenticated()]
    


    @action(detail=False, methods=["GET"])
    def unattempted(self, request):
        if request.user.role != "student":
            return Response({"detail": "Not allowed."}, status=403)

        student = request.user.student
        now = timezone.now()

        # Exams where student has NOT attempted and exam is over
        exams = Exam.objects.filter(end_time__lt=now).exclude(attempts__student=student)
        ser = ExamReadSerializer(exams, many=True)
        return Response(ser.data)

    # ----- student POST /exams/<id>/submit/ -----
    @action(detail=True, methods=["POST"], serializer_class=SubmitExamSerializer)
    def submit(self, request, pk=None):
        exam = self.get_object()
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        attempt, _ = StudentExam.objects.get_or_create(
            student=request.user.student,
            exam=exam,
            defaults={"started_at": timezone.now()}
        )
        if attempt.finished_at:
            return Response({"detail": "You already submitted."}, status=400)

        total, correct = 0, 0
        for ans in ser.validated_data["answers"]:
            total += 1
            try:
                q = Question.objects.get(pk=ans["question_id"], exam=exam)
                opt = Option.objects.get(pk=ans["option_id"], question=q)
            except (Question.DoesNotExist, Option.DoesNotExist):
                continue
            Answer.objects.update_or_create(attempt=attempt, question=q, defaults={"chosen": opt})
            if opt.is_correct:
                correct += 1

        attempt.finished_at = timezone.now()
        attempt.score = (correct / total) * 100 if total else 0
        attempt.status = "attempted" 
        attempt.save()
        return Response({"score": attempt.score})

    # ----- teacher/admin GET /exams/<id>/results/ -----
    @action(detail=True, methods=["GET"])
    def results(self, request, pk=None):
        exam = self.get_object()
        attempts = exam.attempts.select_related("student__user")
        avg = attempts.aggregate(avg=Avg("score"))["avg"]
        return Response({
            "exam": exam.title,
            "average_score": avg,
            "attempts": StudentExamSerializer(attempts, many=True).data
        })
# ─────────────────────────────────────────────
#  PASSWORD‑RESET VIEWS  (add near bottom)
# ─────────────────────────────────────────────
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = User.objects.get(email__iexact=ser.validated_data["email"])
        uid   = urlsafe_base64_encode(smart_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        link = f"http://localhost:5173/reset-password?uid={uid}&token={token}"


        send_mail(
            "Password reset for School App",
            f"Hi {user.first_name or user.username},\n\n"
            f"Use the link below to reset your password:\n{link}\n\n"
            f"If you didn’t ask for this, ignore the e‑mail.",
            from_email=None,                # uses DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            fail_silently=False,
        )
        return Response({"detail": "Reset link sent."})


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Password has been reset."}, status=status.HTTP_200_OK)
class ClassResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        exams = Exam.objects.filter(target_class=class_id)
        data = []

        for exam in exams:
            student_exams = StudentExam.objects.filter(exam=exam).select_related("student__user")
            for se in student_exams:
                data.append({
                    "exam_title": exam.title,
                    "student_name": se.student.user.get_full_name(),
                    "score": se.score,
                    "started_at": se.started_at,
                    "finished_at": se.finished_at,
                })
        return Response(data)

# ─────────────────────────────────────────────
#  CHAT VIEWS 
# ─────────────────────────────────────────────
class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    queryset = Chat.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only chats where the current user is a participant"""
        return Chat.objects.filter(participants=self.request.user)

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get all messages in this chat"""
        chat = self.get_object()
        msgs = chat.messages.select_related("sender").order_by("timestamp")
        return Response(MessageSerializer(msgs, many=True).data)

    def create(self, request, *args, **kwargs):
        user = request.user
        participants_ids = request.data.get("participants", [])

        if len(participants_ids) != 1:
            return Response({"detail": "Provide exactly one other participant ID."}, status=400)

        other = User.objects.filter(id=participants_ids[0]).first()
        if not other:
            return Response({"detail": "User not found."}, status=404)

        # Determine if chat already exists
        existing_chat = Chat.objects.filter(participants=user)\
                            .filter(participants=other)\
                            .distinct()\
                            .first()

        if existing_chat:
            # Return existing chat instead of creating a new one
            serializer = self.get_serializer(existing_chat)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Students → can only chat with assigned teacher
        if user.role == "student":
            if not user.student.assigned_teacher or user.student.assigned_teacher.user_id != other.id:
                return Response({"detail": "Students can only chat with their assigned teacher."}, status=403)
            teacher_user = user.student.assigned_teacher.user
            chat = Chat.objects.create(created_by=user)
            chat.participants.add(user, teacher_user)

        # Teachers → can only chat with their assigned students
        elif user.role == "teacher":
            if not hasattr(other, "student") or other.student.assigned_teacher_id != user.teacher.id:
                return Response({"detail": "Teachers can only chat with their own students."}, status=403)
            chat = Chat.objects.create(created_by=user)
            chat.participants.add(user, other)

        else:
            return Response({"detail": "Only teachers or students can start chats."}, status=403)

        serializer = self.get_serializer(chat, context={"request": request})

        return Response(serializer.data, status=status.HTTP_201_CREATED)
