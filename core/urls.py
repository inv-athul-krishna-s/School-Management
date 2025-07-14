# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    TeacherViewSet,
    StudentViewSet,
    CustomTokenObtainPairView,
    LogoutView,
    TeacherExportView, 
    StudentExportView
)

# ──────────────
#  DRF Router
# ──────────────
router = DefaultRouter()
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("students", StudentViewSet, basename="student")
router.register(r"teachers-export",  TeacherExportView, basename="teacher-export")
router.register(r"students-export",  StudentExportView, basename="student-export")
# ──────────────
#  URL Patterns
# ──────────────
urlpatterns = [
    # JWT auth
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),  # blacklist refresh token

    # Core REST endpoints
    path("", include(router.urls)),
]
