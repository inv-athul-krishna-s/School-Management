from django.contrib import admin
from .models import Answer, Exam, Option, Question, Student, StudentExam, Teacher, User

admin.site.register(User)
admin.site.register(Teacher)
admin.site.register(Student)



admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(StudentExam)
admin.site.register(Answer)