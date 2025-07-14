# core/testing/test_permissions.py
"""
Unit‑tests for:
    • IsAdmin
    • IsTeacher
    • IsStudent
    • IsSelfReadOnly
All TRUE / FALSE and edge‑cases (anonymous, unsafe method, different user) are covered.
"""

from django.test import TestCase, RequestFactory
from rest_framework.request import Request

from core.models import User
from core.permission import (
    IsAdmin,
    IsTeacher,
    IsStudent,
    IsSelfReadOnly,
)


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # three authenticated users with different roles
        self.admin   = User.objects.create_user("adm",   password="x", role="admin")
        self.teacher = User.objects.create_user("teach", password="x", role="teacher")
        self.student = User.objects.create_user("stud",  password="x", role="student")

        # an “anonymous” request
        self.anon_req = Request(self.factory.get("/"))

    # ───────────────────────── helpers ──────────────────────────
    def _req(self, user, method="GET"):
        """Return a DRF Request with given user & HTTP method."""
        django_req = self.factory.generic(method, "/")
        req = Request(django_req)
        req.user = user
        return req

    def _dummy_obj_for(self, user):
        """Simple object that carries a .user attribute for IsSelfReadOnly."""
        return type("Dummy", (), {"user": user})()

    # ───────────────────────── IsAdmin ──────────────────────────
    def test_is_admin(self):
        perm = IsAdmin()

        self.assertTrue(perm.has_permission(self._req(self.admin),   view=None))
        self.assertFalse(perm.has_permission(self._req(self.teacher), view=None))
        self.assertFalse(perm.has_permission(self._req(self.student), view=None))
        self.assertFalse(perm.has_permission(self.anon_req,           view=None))

    # ───────────────────────── IsTeacher ────────────────────────
    def test_is_teacher(self):
        perm = IsTeacher()

        self.assertTrue(perm.has_permission(self._req(self.teacher), view=None))
        self.assertFalse(perm.has_permission(self._req(self.admin),  view=None))
        self.assertFalse(perm.has_permission(self._req(self.student), view=None))
        self.assertFalse(perm.has_permission(self.anon_req,           view=None))

    # ───────────────────────── IsStudent ────────────────────────
    def test_is_student(self):
        perm = IsStudent()

        self.assertTrue(perm.has_permission(self._req(self.student), view=None))
        self.assertFalse(perm.has_permission(self._req(self.admin),  view=None))
        self.assertFalse(perm.has_permission(self._req(self.teacher), view=None))
        self.assertFalse(perm.has_permission(self.anon_req,           view=None))

    # ─────────────────────── IsSelfReadOnly ─────────────────────
    def test_is_self_read_only_success_and_failures(self):
        perm = IsSelfReadOnly()
        obj  = self._dummy_obj_for(self.student)

        # SAFE method (GET) & same user  → allowed
        self.assertTrue(
            perm.has_object_permission(
                self._req(self.student, method="GET"),   view=None, obj=obj
            )
        )

        # SAFE method but different user → denied
        self.assertFalse(
            perm.has_object_permission(
                self._req(self.teacher, method="GET"),   view=None, obj=obj
            )
        )

        # UNSAFE method (PATCH) even for same user → denied
        self.assertFalse(
            perm.has_object_permission(
                self._req(self.student, method="PATCH"), view=None, obj=obj
            )
        )

        # Anonymous user always denied
        self.assertFalse(
            perm.has_object_permission(
                self.anon_req, view=None, obj=obj
            )
        )