import csv
from io import StringIO
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import permissions


class CSVExportMixin:
    """
    Mixin to export queryset to CSV.
    Must define:
        - csv_fields: List of model field paths (e.g. user__username)
        - csv_headers: Optional list of column headers (same length as csv_fields)
        - csv_filename: Filename of downloaded CSV
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if getattr(request.user, "role", "") != "admin":
            return Response({"detail": "Only admin can export."}, status=403)

        queryset = self.filter_queryset(self.get_queryset())
        fields = getattr(self, "csv_fields", [])
        headers = getattr(self, "csv_headers", fields)
        filename = getattr(self, "csv_filename", "export.csv")

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)  # First row as column headers

        for obj in queryset:
            row = [self.resolve_nested_attr(obj, field) for field in fields]
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def resolve_nested_attr(obj, attr_path):
        """Safely resolve nested attributes like 'user__username'."""
        try:
            for part in attr_path.split("__"):
                obj = getattr(obj, part)
                if obj is None:
                    return ""
            return str(obj)
        except AttributeError:
            return ""