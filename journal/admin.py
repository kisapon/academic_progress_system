from django.contrib import admin
from .models import Attendance, FinalGrade, Grade, Lesson, Profile, Student, StudyGroup, Subject, Teacher, TeacherAssignment

admin.site.register(Profile)
admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(StudyGroup)
admin.site.register(Subject)
admin.site.register(TeacherAssignment)
admin.site.register(Lesson)
admin.site.register(Grade)
admin.site.register(Attendance)
admin.site.register(FinalGrade)
