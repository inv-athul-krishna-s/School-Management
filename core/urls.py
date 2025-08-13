# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import ClassResultsView, PasswordResetRequestView, PasswordResetConfirmView
    
from .views import ChatViewSet


from .views import (
    TeacherViewSet,
    StudentViewSet,
    CustomTokenObtainPairView,
    LogoutView,
    TeacherExportView, 
    StudentExportView,
    ExamViewSet,
)

# ──────────────
#  DRF Router
# ──────────────
router = DefaultRouter()
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("students", StudentViewSet, basename="student")
router.register(r"teachers-export",  TeacherExportView, basename="teacher-export")
router.register(r"students-export",  StudentExportView, basename="student-export")
router.register("exams",           ExamViewSet,         basename="exam") 


# Chat endpoints
router.register("chats", ChatViewSet, basename="chat")

# ──────────────
#  URL Patterns
# ──────────────
urlpatterns = [
    # JWT auth
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),  # blacklist refresh token
    path("password-reset/request/",  PasswordResetRequestView.as_view(),  name="password_reset_request"),
    path("password-reset/confirm/",  PasswordResetConfirmView.as_view(),  name="password_reset_confirm"),

    path("results/class/<int:class_id>/", ClassResultsView.as_view(), name="class-results"),

    # Core REST endpoints
    path("", include(router.urls)),

    
]
