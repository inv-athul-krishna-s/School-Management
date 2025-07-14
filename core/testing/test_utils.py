# core/testing/test_utils_csv_mixin.py
from io import StringIO
import csv

from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory

from core.models import User, Teacher, Student
from core.views import StudentExportView, TeacherExportView
from core.utils import CSVExportMixin


class CSVExportMixinUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        #── Users ────────────────────────────────────────────────────────────
        cls.admin   = User.objects.create_user("admin",  password="x", role="admin")
        cls.teacher = User.objects.create_user("teach",  password="x", role="teacher")
        cls.student = User.objects.create_user("stud",   password="x", role="student")

        #── Domain data (one record each is enough) ──────────────────────────
        cls.teacher_rec = Teacher.objects.create(
            user=cls.teacher,
            phone="999",
            subject_specialization="Physics",
            employee_id="E1",
            date_of_joining="2024-01-01",
            status="active",
        )
        cls.student_rec = Student.objects.create(
            user=cls.student,
            phone="888",
            roll_number="R1",
            student_class="10-A",
            date_of_birth="2010-02-02",
            admission_date="2024-02-02",
            status="active",
            assigned_teacher=cls.teacher_rec,
        )

    # ───────────────────────────── helper ──────────────────────────────────
    def _client_with_token(self, user):
        """Return an APIClient already logged‑in with JWT header."""
        client = APIClient()
        res = client.post(reverse("token_obtain_pair"), {"username": user.username, "password": "x"}, format="json")
        token = res.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    # ─────────────────────────── positive case ─────────────────────────────
    def test_admin_can_export_students_csv(self):
        client = self._client_with_token(self.admin)
        res = client.get(reverse("student-export-list"))
        self.assertEqual(res.status_code, 200)

        # check headers
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("students.csv", res["Content-Disposition"])

        # parse CSV content
        csv_body = res.content.decode("utf‑8")
        reader = csv.reader(StringIO(csv_body))
        rows = list(reader)

        # first row should be the configured header list
        expected_header = StudentExportView.csv_headers
        self.assertEqual(rows[0], expected_header)

        # one exported data row
        self.assertEqual(len(rows), 2)
        # Username column (index 1) should match
        self.assertEqual(rows[1][1], self.student.username)

    # ─────────────────────────── forbidden cases ───────────────────────────
    def test_non_admin_cannot_export_teachers(self):
        for user in (self.teacher, self.student):
            client = self._client_with_token(user)
            res = client.get(reverse("teacher-export-list"))
            self.assertEqual(res.status_code, 403)

    # ───────────────── resolve_nested_attr helper ──────────────────────────
    def test_resolve_nested_attr(self):
        mixin = CSVExportMixin()

        # simple path
        val = mixin.resolve_nested_attr(self.student_rec, "user__username")
        self.assertEqual(val, self.student.username)

        # attribute chain hits None midway  -> empty string
        self.student_rec.assigned_teacher = None
        self.assertEqual(
            mixin.resolve_nested_attr(self.student_rec, "assigned_teacher__user__username"),
            "",
        )

        # missing attribute -> empty string, no crash
        self.assertEqual(mixin.resolve_nested_attr(self.student_rec, "does_not_exist"), "")
