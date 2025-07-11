import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import User, Teacher, Student


pytestmark = pytest.mark.django_db


def api_client():
    """Always return a fresh APIClient (not the default Django client)."""
    return APIClient()


def jwt_headers(username, password):
    """Login helper → returns headers with Bearer token."""
    client = api_client()
    r = client.post(
        reverse("token_obtain_pair"),
        {"username": username, "password": password},
        format="json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {r.data['access']}"}


class TestRolePermissions:
    def setup_method(self):
        # Admin
        self.admin = User.objects.create_user("admin", password="adm123", role="admin")

        # Teacher + profile
        self.t_user = User.objects.create_user("teach", password="teach123", role="teacher")
        self.teacher = Teacher.objects.create(
            user=self.t_user,
            phone="999",
            subject_specialization="Math",
            employee_id="T001",
            date_of_joining=date.today(),
            status="active",
        )

        # Student assigned to teacher
        self.s_user = User.objects.create_user("stud", password="stud123", role="student")
        self.student = Student.objects.create(
            user=self.s_user,
            phone="888",
            roll_number="R1",
            student_class="10-A",
            date_of_birth="2010-05-01",
            admission_date="2024-04-01",
            status="active",
            assigned_teacher=self.teacher,
        )

    # ─────────────────── Admin CRUD ────────────────────
    def test_admin_creates_student(self):
        client = api_client()
        hdr = jwt_headers("admin", "adm123")
        payload = {
            "user": {
                "username": "stud2",
                "password": "pwd",
                "email": "stud2@example.com",
                "first_name": "New",
                "last_name": "Student",
                "phone": "1112223333",
            },
            "phone": "777",
            "roll_number": "R2",
            "student_class": "9-B",
            "date_of_birth": "2011-02-02",
            "admission_date": "2024-02-01",
            "status": "active",
            "assigned_teacher": self.teacher.id,
        }
        r = client.post(reverse("student-list"), payload, format="json", **hdr)
        assert r.status_code == status.HTTP_201_CREATED

    # ─────────────────── Teacher rules ─────────────────
    def test_teacher_cannot_create_teacher(self):
        client = api_client()
        hdr = jwt_headers("teach", "teach123")
        r = client.post(reverse("teacher-list"), {}, format="json", **hdr)
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_updates_assigned_student(self):
        client = api_client()
        hdr = jwt_headers("teach", "teach123")
        url = reverse("student-detail", args=[self.student.id])
        r = client.patch(url, {"status": "inactive"}, format="json", **hdr)
        assert r.status_code == status.HTTP_200_OK
        self.student.refresh_from_db()
        assert self.student.status == "inactive"

    def test_teacher_cannot_update_unassigned_student(self):
        other_u = User.objects.create_user("othstud", password="x", role="student")
        other_s = Student.objects.create(
            user=other_u,
            phone="123",
            roll_number="R99",
            student_class="9-A",
            date_of_birth="2011-01-01",
            admission_date="2024-01-01",
            status="active",
            assigned_teacher=None,
        )
        client = api_client()
        hdr = jwt_headers("teach", "teach123")
        r = client.patch(
            reverse("student-detail", args=[other_s.id]),
            {"status": "inactive"},
            format="json",
            **hdr,
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    # ─────────────────── Student rules ─────────────────
    def test_student_view_me(self):
        client = api_client()
        hdr = jwt_headers("stud", "stud123")
        r = client.get(reverse("student-me"), **hdr)
        assert r.status_code == 200
        assert r.data["user"]["username"] == "stud"

    def test_student_cannot_create_student(self):
        client = api_client()
        hdr = jwt_headers("stud", "stud123")
        r = client.post(reverse("student-list"), {}, format="json", **hdr)
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_update_any(self):
        client = api_client()
        hdr = jwt_headers("stud", "stud123")
        r = client.patch(
            reverse("student-detail", args=[self.student.id]),
            {"status": "inactive"},
            format="json",
            **hdr,
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    # ─────────────────── Logout / blacklist ────────────
    def test_logout_blacklists_refresh(self):
        client = api_client()
        login = client.post(
            reverse("token_obtain_pair"),
            {"username": "admin", "password": "adm123"},
            format="json",
        )
        refresh = login.data["refresh"]

        logout_r = client.post(reverse("logout"), {"refresh": refresh}, format="json")
        assert logout_r.status_code == status.HTTP_205_RESET_CONTENT

        bad = client.post(reverse("token_refresh"), {"refresh": refresh}, format="json")
        assert bad.status_code == status.HTTP_401_UNAUTHORIZED
