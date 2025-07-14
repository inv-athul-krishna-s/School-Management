# core/testing/test_models_extra.py
import pytest
from core.models import User, Student


@pytest.mark.django_db
def test_student_delete_also_deletes_user():
    u = User.objects.create_user("tmp", "t@x.com", "pwd", role="student")
    s = Student.objects.create(
        user=u,
        phone="1",
        roll_number="ROLL1",
        student_class="10",
        date_of_birth="2000-01-01",
        admission_date="2024-01-01",
        status="active",
    )

    s.delete()
    assert Student.objects.count() == 0
    assert User.objects.filter(pk=u.pk).count() == 0
