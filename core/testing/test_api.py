import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import User, Teacher, Student
import json
pytestmark = pytest.mark.django_db


def token_header(username, password):
    """
    Helper: returns headers incl. Authorization Bearer <access>
    """
    client = APIClient()
    url = reverse("token_obtain_pair")
    r = client.post(url, {"username": username, "password": password}, format="json")
    access = r.data["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


class TestRolePermissions:
    def setup_method(self):
        # Admin
        self.admin = User.objects.create_user("admin", password="admin123", role="admin")

        # Teacher + profile
        self.t_user = User.objects.create_user("teach", password="teach123", role="teacher")
        self.teacher = Teacher.objects.create(
            user=self.t_user,
            phone="123",
            subject_specialization="Maths",
            employee_id="EMP1",
            date_of_joining=date.today(),
            status="active",
        )

        # Student for teacher
        self.s_user = User.objects.create_user("stud", password="stud123", role="student")
        self.student = Student.objects.create(
            user=self.s_user,
            phone="456",
            roll_number="R1",
            student_class="10-A",
            date_of_birth="2010-01-01",
            admission_date="2024-01-01",
            status="active",
            assigned_teacher=self.teacher,
        )

    # ---------- Admin CRUD ----------

    def test_admin_can_create_student(self, client):
        hdr = token_header("admin", "admin123")
        payload = {
    "user": {
        "username": "stud2",
        "password": "pwd",
        "email": "stud2@example.com",
        "first_name": "Test",
        "last_name": "Student"
    },
    "phone": "789",
    "roll_number": "R2",
    "student_class": "9-B",
    "date_of_birth": "2011-02-02",
    "admission_date": "2024-02-01",
    "status": "active",
    "assigned_teacher": self.teacher.id,
}

        url = reverse("student-list")
        r = client.post(url, payload, format="json", **hdr)
        print("Response data:", r.data)

        assert r.status_code == status.HTTP_201_CREATED

    # ---------- Teacher rules ----------

    def test_teacher_cannot_create_teacher(self, client):
        hdr = token_header("teach", "teach123")
        url = reverse("teacher-list")
        r = client.post(url, {}, format="json", **hdr)
        print("Response data:", r.data)

        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_can_update_assigned_student(self, client):
        hdr = token_header("teach", "teach123")
        url = reverse("student-detail", args=[self.student.id])
        r = client.patch(
    url,
    data=json.dumps({"status": "inactive"}),
    content_type="application/json",
    **hdr
)
        print("Response data:", r.data)

        assert r.status_code == status.HTTP_200_OK
        self.student.refresh_from_db()
        print("Response data:", r.data)

        assert self.student.status == "inactive"

    # ---------- Student rules ----------

    def test_student_view_me(self, client):
        hdr = token_header("stud", "stud123")
        r = client.get(reverse("student-me"), **hdr)
        print("Response data:", r.data)

        assert r.status_code == 200
        print("Response data:", r.data)

        assert r.data["user"]["username"] == "stud"

    def test_student_cannot_create_student(self, client):
        hdr = token_header("stud", "stud123")
        r = client.post(reverse("student-list"), {}, **hdr)
        print("Response data:", r.data)

        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_update_anyone(self, client):
        hdr = token_header("stud", "stud123")
        url = reverse("student-detail", args=[self.student.id])
        r = client.patch(url, {"status": "inactive"}, format="json", **hdr)
        print("Response data:", r.data)

        assert r.status_code == status.HTTP_403_FORBIDDEN

    # ---------- Logout ----------

    def test_logout_blacklists_refresh(self, client):
        login = client.post(
            reverse("token_obtain_pair"),
            {"username": "admin", "password": "admin123"},
            format="json",
        )
        refresh = login.data["refresh"]

        r_logout = client.post(reverse("logout"), {"refresh": refresh}, format="json")
        
        assert r_logout.status_code == status.HTTP_205_RESET_CONTENT

        # token can no longer be refreshed
        bad = client.post(reverse("token_refresh"), {"refresh": refresh}, format="json")
     

        assert bad.status_code == status.HTTP_401_UNAUTHORIZED
