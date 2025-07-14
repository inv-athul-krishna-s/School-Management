# core/testing/test_serializers_extra.py
import pytest
from django.contrib.auth import get_user_model

from core.serializers import (
    BaseUserSerializer,
    TeacherUserSerializer,
    StudentUserSerializer,
)

User = get_user_model()


@pytest.mark.django_db
def test_validate_username_duplicate_error():
    """
    Lines 17‑23: duplicate username path raises ValidationError.
    """
    User.objects.create_user(username="taken", password="x", role="admin")

    s = BaseUserSerializer(data={"username": "taken"})
    assert not s.is_valid()
    assert "username" in s.errors  # ValidationError captured


@pytest.mark.django_db
def test_autogenerate_password_when_missing():
    """
    Lines 31‑34 & 38 (auto‑password branch).
    """
    payload = {
        "username": "nopass",
        "email": "n@n.com",
        "first_name": "No",
        "last_name": "Pass",
    }
    s = BaseUserSerializer(data=payload)
    assert s.is_valid(), s.errors  # <-- this line is the key fix

    user = s.save()
    assert user.username == "nopass"
    assert user.check_password("nopass123")


@pytest.mark.django_db
def test_teacher_and_student_user_serializers_set_role():
    """
    Lines 54‑66 & 76‑88: Teacher / Student role injection.
    """
    t_user = TeacherUserSerializer().create(
        {"username": "teachGuy", "password": "t", "email": "t@g.com", "first_name": "T", "last_name": "G"}
    )
    s_user = StudentUserSerializer().create(
        {"username": "studGal", "password": "s", "email": "s@g.com", "first_name": "S", "last_name": "G"}
    )

    assert t_user.role == "teacher"
    assert s_user.role == "student"