from django.db import migrations, connection

def truncate_tables(apps, schema_editor):
    with connection.cursor() as cursor:
        # Disable foreign key checks (SQLite syntax)
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Delete records instead of TRUNCATE
        cursor.execute("DELETE FROM core_student;")
        cursor.execute("DELETE FROM core_teacher;")

        # Re-enable foreign key checks
        cursor.execute("PRAGMA foreign_keys = ON;")

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),  # replace with your last migration
    ]

    operations = [
        migrations.RunPython(truncate_tables, reverse_code=migrations.RunPython.noop),
    ]
