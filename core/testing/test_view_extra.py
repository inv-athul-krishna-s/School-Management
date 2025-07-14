# core/testing/test_views_extra.py
import csv, io
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User, Teacher, Student


@pytest.fixture
def api():
    return APIClient()


def auth(client, username, password):
    token_url = reverse("token_obtain_pair")
    r = client.post(token_url, {"username": username, "password": password})
    client.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])


@pytest.mark.django_db
def test_admin_can_export_teachers_csv(api):
    admin = User.objects.create_user("adm", password="adm", role="admin")
    teach_user = User.objects.create_user("t", password="t", role="teacher")
    Teacher.objects.create(
        user=teach_user,
        phone="1",
        subject_specialization="Math",
        employee_id="E1",
        date_of_joining="2020-01-01",
        status="active",
    )
    auth(api, "adm", "adm")
    url = reverse("teacher-export-list")  # defined by DefaultRouter
    resp = api.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["content-type"] == "text/csv"
    rows = list(csv.reader(io.StringIO(resp.content.decode())))
    assert rows[0] == ["ID", "Username", "Email", "First Name", "Last Name",
                       "Subject", "Employee ID", "Joined On", "Status"]
    assert rows[1][1] == "t"  # username column


@pytest.mark.django_db
def test_teacher_cannot_patch_unassigned_student(api):
    # make teacher + student belonging to *another* teacher
    main_teacher_user = User.objects.create_user("teach", "t@x.com", "pwd", role="teacher")
    other_teacher_user = User.objects.create_user("other", "o@x.com", "pwd", role="teacher")
    main_teacher      = Teacher.objects.create(user=main_teacher_user, phone="9",
                          subject_specialization="Sci", employee_id="E9",
                          date_of_joining="2021-01-01", status="active")
    other_teacher     = Teacher.objects.create(user=other_teacher_user, phone="8",
                          subject_specialization="Eng", employee_id="E8",
                          date_of_joining="2021-01-01", status="active")
    stud_u = User.objects.create_user("stu","s@x.com","pwd",role="student")
    Student.objects.create(user=stud_u, phone="1", roll_number="R1",
        student_class="10-A", date_of_birth="2010-01-01",
        admission_date="2024-01-01", status="active",
        assigned_teacher=other_teacher)

    auth(api, "teach", "pwd")
    url = reverse("student-detail", args=[1])
    r = api.patch(url, {"status": "inactive"}, format="json")
    assert r.status_code == status.HTTP_404_NOT_FOUND

