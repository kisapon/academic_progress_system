from .utils import get_role, is_admin, is_teacher, is_student


def role_context(request):
    user = getattr(request, 'user', None)
    return {
        'current_role': get_role(user) if user and user.is_authenticated else None,
        'is_role_admin': is_admin(user) if user and user.is_authenticated else False,
        'is_role_teacher': is_teacher(user) if user and user.is_authenticated else False,
        'is_role_student': is_student(user) if user and user.is_authenticated else False,
    }
