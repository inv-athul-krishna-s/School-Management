import csv, io
from datetime import date
from django.test import RequestFactory, TestCase
from rest_framework import permissions
from core.models import User, Teacher
from core.utils import CSVExportMixin
from core.views import TeacherViewSet  # reuse queryset / serializer


class DummyCSVView(CSVExportMixin, TeacherViewSet):
    """
    Minimal concrete subclass to unit‑test the mixin alone
    (bypasses router / DRF default behaviour).
    """
    permission_classes = [permissions.AllowAny]  # ignore auth for this test
    csv_fields = ["employee_id"]


class CSVExportMixinUnitTest(TestCase):
    def setUp(self):
        user = User.objects.create_user("teach", password="x", role="teacher")
        Teacher.objects.create(
            user=user,
            phone="0",
            subject_specialization="Sci",
            employee_id="EMPX",
            date_of_joining=date(2024, 1, 1),
            status="active",
        )
        self.factory = RequestFactory()

    def test_list_returns_csv(self):
        req = self.factory.get("/dummy/")
        req.user = User.objects.create_user("admin", password="x", role="admin")
        view = DummyCSVView.as_view({"get": "list"})
        resp = view(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

        rows = list(csv.reader(io.StringIO(resp.content.decode())))
        self.assertEqual(rows[0], ["employee_id"])
        self.assertEqual(rows[1][0], "EMPX")
