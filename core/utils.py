import csv
from django.db import router
from django.http import HttpResponse

class CSVExportMixin:
    """
    Return queryset as CSV.  Override `csv_filename` & `csv_fields`.
    Only GET allowed.
    """
    csv_filename = "export.csv"
    csv_fields = []

    def list(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return response({"detail": "Only admin can export."}, status=403)

        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{self.csv_filename}"'

        writer = csv.writer(response)
        writer.writerow(self.csv_fields)
        for obj in qs:
            writer.writerow([getattr(obj, f) for f in self.csv_fields])
        return response
# core/urls.py
from .views import TeacherExportView, StudentExportView

router.register(r'teachers/export', TeacherExportView, basename='teacher-export')
router.register(r'students/export', StudentExportView, basename='student-export')
