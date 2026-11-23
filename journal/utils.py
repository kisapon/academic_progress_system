from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'admin'
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def is_admin(user):
    return get_role(user) == 'admin'


def is_teacher(user):
    return get_role(user) == 'teacher'


def is_student(user):
    return get_role(user) == 'student'


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Недостаточно прав доступа для выполнения действия.')
            return redirect('dashboard')
        return wrapper
    return decorator


def teacher_can_access_lesson(user, lesson):
    if is_admin(user):
        return True
    if is_teacher(user):
        teacher = getattr(user, 'teacher_profile', None)
        return teacher and lesson.teacher_id == teacher.id
    if is_student(user):
        student = getattr(user, 'student_profile', None)
        return student and lesson.group_id == student.group_id
    return False


def teacher_can_access_student(user, student):
    if is_admin(user):
        return True
    if is_student(user):
        own = getattr(user, 'student_profile', None)
        return own and own.id == student.id
    if is_teacher(user):
        teacher = getattr(user, 'teacher_profile', None)
        if not teacher:
            return False
        return student.group.assignments.filter(teacher=teacher).exists()
    return False
