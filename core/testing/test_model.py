import pytest
from datetime import date
from core.models import User, Teacher, Student

pytestmark = pytest.mark.django_db


def test_user_str():
    u = User.objects.create_user("bob", password="x", role="teacher")
    assert str(u) == "bob (teacher)"


def test_teacher_str():
    t_user = User.objects.create_user("teach", password="x", role="teacher")
    teacher = Teacher.objects.create(
        user=t_user,
        phone="111",
        subject_specialization="Physics",
        employee_id="EMP1",
        date_of_joining=date.today(),
        status="active",
    )
    assert "Physics" in str(teacher)


def test_student_delete_removes_user():
    s_user = User.objects.create_user("stud", password="x", role="student")
    stud = Student.objects.create(
        user=s_user,
        phone="000",
        roll_number="R1",
        student_class="10-A",
        date_of_birth="2010-01-01",
        admission_date="2024-01-01",
        status="active",
    )
    stud.delete()
    assert not User.objects.filter(pk=s_user.pk).exists()