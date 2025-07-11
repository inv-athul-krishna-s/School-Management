import csv
import io
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from core.models import User, Teacher, Student


class CSVExportEndpointTests(TestCase):
    """Verify /api/teachers/export/ and /api/students/export/."""

    def setUp(self):
        # --- users --------------------------------------------------
        self.admin   = User.objects.create_user("admin",  password="adm", role="admin")
        self.teacher = User.objects.create_user("teach1", password="pwd", role="teacher")
        self.student = User.objects.create_user("stud1",  password="pwd", role="student")

        # --- teacher profile ---------------------------------------
        self.t_profile = Teacher.objects.create(
            user=self.teacher,
            phone="111",
            subject_specialization="Math",
            employee_id="EMP001",
            date_of_joining=date(2024, 1, 1),
            status="active",
        )

        # --- student profile ---------------------------------------
        Student.objects.create(
            user=self.student,
            phone="222",
            roll_number="R1",
            student_class="10-A",
            date_of_birth="2010-01-01",
            admission_date="2024-02-01",
            status="active",
            assigned_teacher=self.t_profile,
        )

        self.client = APIClient()

    # -- helper -----------------------------------------------------
    def bearer(self, username, password):
        token = self.client.post(
            reverse("token_obtain_pair"),
            {"username": username, "password": password},
            format="json",
        ).data["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # ------------------- admin success cases -----------------------
    def test_admin_can_export_teachers(self):
        url = reverse("teacher-export-list")
        r = self.client.get(url, **self.bearer("admin", "adm"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/csv")

        # parse CSV
        rows = list(csv.reader(io.StringIO(r.content.decode())))
        self.assertGreaterEqual(len(rows), 2)  # header + 1 teacher row
        self.assertIn("EMP001", ",".join(rows[1]))

    def test_admin_can_export_students(self):
        url = reverse("student-export-list")
        r = self.client.get(url, **self.bearer("admin", "adm"))
        self.assertEqual(r.status_code, 200)
        rows = list(csv.reader(io.StringIO(r.content.decode())))
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("R1", ",".join(rows[1]))

    # ------------------- forbidden cases ---------------------------
    def test_teacher_cannot_export(self):
        url = reverse("teacher-export-list")
        r = self.client.get(url, **self.bearer("teach1", "pwd"))
        self.assertEqual(r.status_code, 403)

    def test_student_cannot_export(self):
        url = reverse("student-export-list")
        r = self.client.get(url, **self.bearer("stud1", "pwd"))
        self.assertEqual(r.status_code, 403)
