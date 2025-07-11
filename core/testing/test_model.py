import pytest
from datetime import date
from core.models import User, Teacher, Student

pytestmark = pytest.mark.django_db  # all tests in this file hit the DB

def test_user_str():
    user = User.objects.create_user(username="alice", password="x", role="teacher")
    assert str(user) == "alice (teacher)"

def test_teacher_str():
    t_user = User.objects.create_user(username="teach", password="x", role="teacher")
    teacher = Teacher.objects.create(
        user=t_user,
        phone="111",
        subject_specialization="Physics",
        employee_id="EMP1",
        date_of_joining=date.today(),
        status="active",
    )
    assert "Physics" in str(teacher)

def test_student_delete_cascades_user():
    s_user = User.objects.create_user(username="stud", password="x", role="student")
    student = Student.objects.create(
        user=s_user,
        phone="222",
        roll_number="R1",
        student_class="10-A",
        date_of_birth="2010-01-01",
        admission_date="2024-01-01",
        status="active",
    )
    student.delete()
    assert not User.objects.filter(pk=s_user.pk).exists()
