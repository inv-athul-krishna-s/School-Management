from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "teacher"

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "student"
    
from rest_framework.permissions import BasePermission

class IsTeacherOwner(BasePermission):
    """
    Allows access only to the teacher who created the exam.
    """
    def has_object_permission(self, request, view, obj):
        teacher = getattr(request.user, 'teacher', None)
        return teacher and obj.teacher == teacher

class IsStudentOfTeacher(BasePermission):
    """
    Student can access only objects that belong to their *assigned* teacher.
    """
    def has_object_permission(self, request, view, obj):
        student_profile = getattr(request.user, "student", None)
        return (
            student_profile
            and student_profile.assigned_teacher == obj.teacher   # <‑‑ fix here
        )


class IsSelfReadOnly(BasePermission):
    """GET/HEAD/OPTIONS only & only on own object"""
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS and request.user == obj.user