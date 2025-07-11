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

class IsSelfReadOnly(BasePermission):
    """GET/HEAD/OPTIONS only & only on own object"""
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS and request.user == obj.user