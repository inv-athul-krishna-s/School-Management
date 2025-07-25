# core/testing/test_views_crud.py
import datetime as dt
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import User, Teacher, Student

def jwt_header(username: str, pwd="x"):
    client = APIClient()
    r = client.post(reverse("token_obtain_pair"), {"username": username, "password": pwd}, format="json")
    return {"HTTP_AUTHORIZATION": f"Bearer {r.data['access']}"}

def _bootstrap():
    """Create one admin, one teacher & one student."""
    admin   = User.objects.create_user("admin",   password="x", role="admin")
    teacher = User.objects.create_user("teach",   password="x", role="teacher")
    stud    = User.objects.create_user("stud",    password="x", role="student")

    t_rec = Teacher.objects.create(
        user=teacher, phone="1", subject_specialization="Math",
        employee_id="E1", date_of_joining=dt.date.today(), status="active"
    )
    Student.objects.create(
        user=stud, phone="2", roll_number="R1", student_class="10-A",
        date_of_birth=dt.date(2010,1,1), admission_date=dt.date.today(),
        status="active", assigned_teacher=t_rec
    )
    return admin, teacher, stud, t_rec

# ────────────────────────────────────────────────────────────────
def test_admin_can_create_teacher():
    admin, *_ = _bootstrap()
    hdr  = jwt_header(admin.username)

    payload = {
        "user": {
            "username": "newteach",
            "password": "x",
            "email": "t@x.com"
        },
        "phone": "123",
        "subject_specialization": "Physics",
        "employee_id": "E99",
        "date_of_joining": "2024-01-01",
        "status": "active"
    }
    client = APIClient()
    r = client.post(reverse("teacher-list"), payload, format="json", **hdr)
    assert r.status_code == status.HTTP_201_CREATED
    assert Teacher.objects.filter(employee_id="E99").exists()

# ────────────────────────────────────────────────────────────────
def test_teacher_cannot_delete_teacher():
    admin, teacher, *_ = _bootstrap()
    hdr = jwt_header(teacher.username)
    client = APIClient()
    target_id = Teacher.objects.get(user=teacher).id
    r = client.delete(reverse("teacher-detail", args=[target_id]), **hdr)
    assert r.status_code == status.HTTP_403_FORBIDDEN

# ────────────────────────────────────────────────────────────────
def test_teacher_can_patch_assigned_student():
    admin, teacher, stud, *_ = _bootstrap()
    hdr_admin   = jwt_header(admin.username)
    hdr_teacher = jwt_header(teacher.username)
    client      = APIClient()

    # admin creates a second student assigned to the same teacher
    new_stud_payload = {
        "user": {"username": "stu2", "password": "x"},
        "phone": "22",
        "roll_number": "R2",
        "student_class": "10-B",
        "date_of_birth": "2011-02-02",
        "admission_date": "2025-01-01",
        "status": "active",
        "assigned_teacher": Teacher.objects.get(user=teacher).id
    }
    r = client.post(reverse("student-list"), new_stud_payload, format="json", **hdr_admin)
    assert r.status_code == 201
    sid = r.data["id"]

    # teacher patches the status
    r = client.patch(reverse("student-detail", args=[sid]), {"status": "inactive"}, format="json", **hdr_teacher)
    assert r.status_code == 200
    assert r.data["status"] == "inactive"