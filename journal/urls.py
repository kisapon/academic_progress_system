from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),

    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),

    path('schedule/', views.schedule_list, name='schedule_list'),
    path('schedule/create/', views.lesson_create, name='lesson_create'),
    path('schedule/<int:pk>/', views.lesson_detail, name='lesson_detail'),
    path('schedule/<int:pk>/edit/', views.lesson_edit, name='lesson_edit'),
    path('schedule/<int:pk>/delete/', views.lesson_delete, name='lesson_delete'),

    path('final-grades/', views.final_grade_list, name='final_grade_list'),
    path('final-grades/create/', views.final_grade_create, name='final_grade_create'),
    path('final-grades/<int:pk>/edit/', views.final_grade_edit, name='final_grade_edit'),
    path('final-grades/<int:pk>/delete/', views.final_grade_delete, name='final_grade_delete'),

    path('reports/', views.reports_index, name='reports_index'),
    path('reports/activity/', views.report_activity, name='report_activity'),
    path('reports/student/', views.report_student, name='report_student'),
    path('reports/subject-group/', views.report_subject_group, name='report_subject_group'),
    path('reports/performance/', views.report_performance_statistics, name='report_performance_statistics'),
    path('reports/attendance/', views.report_attendance_statistics, name='report_attendance_statistics'),
    path('reports/final/', views.report_final_statement, name='report_final_statement'),
]
