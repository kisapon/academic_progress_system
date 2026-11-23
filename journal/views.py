from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    FinalGradeForm,
    LessonForm,
    ReportFilterForm,
    StudyGroupForm,
    SubjectForm,
    TeacherAssignmentForm,
    TeacherLessonEditForm,
    UserCreateForm,
    UserUpdateForm,
)
from .models import Attendance, FinalGrade, Grade, Lesson, Student, StudyGroup, Subject, TeacherAssignment
from .services import (
    attendance_statistics,
    final_statement,
    journal_activity_report,
    performance_statistics,
    student_current_report,
    subject_group_report,
)
from .utils import get_role, is_admin, is_student, is_teacher, role_required, teacher_can_access_lesson, teacher_can_access_student


def save_form(request, form, title, success_message, redirect_to):
    """Общий обработчик страниц создания и редактирования."""
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, success_message)
        return redirect(redirect_to)
    return render(request, 'journal/form.html', {'form': form, 'title': title})


def delete_object(request, obj, title, success_message, redirect_to):
    """Общий обработчик страниц удаления."""
    if request.method == 'POST':
        obj.delete()
        messages.success(request, success_message)
        return redirect(redirect_to)
    return render(request, 'journal/confirm_delete.html', {'object': obj, 'title': title})


def teacher_limited_form(form, user):
    """Оставляет преподавателю только закрепленные группы и предметы."""
    if is_teacher(user):
        teacher = user.teacher_profile
        form.fields['group'].queryset = form.fields['group'].queryset.filter(assignments__teacher=teacher).distinct()
        form.fields['subject'].queryset = form.fields['subject'].queryset.filter(assignments__teacher=teacher).distinct()
        return teacher
    return None


def selected_student_for_report(user, form):
    return getattr(user, 'student_profile', None) if is_student(user) else form.cleaned_data.get('student')


@login_required
def dashboard(request):
    return render(request, 'journal/dashboard.html', {'role': get_role(request.user)})


@role_required('admin')
def user_list(request):
    users = User.objects.select_related('profile').order_by('last_name', 'first_name', 'username')
    return render(request, 'journal/user_list.html', {'users': users})


@role_required('admin')
def user_create(request):
    return save_form(request, UserCreateForm(request.POST or None), 'Создание пользователя', 'Пользователь создан.', 'user_list')


@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    return save_form(request, UserUpdateForm(request.POST or None, instance=user), 'Редактирование пользователя', 'Данные пользователя обновлены.', 'user_list')


@role_required('admin')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST' and user == request.user:
        messages.error(request, 'Нельзя удалить текущего пользователя.')
        return redirect('user_list')
    return delete_object(request, user, 'Удаление пользователя', 'Пользователь удален.', 'user_list')


@role_required('admin')
def group_list(request):
    groups = StudyGroup.objects.select_related('curator__user__profile').prefetch_related('students')
    return render(request, 'journal/group_list.html', {'groups': groups})


@role_required('admin')
def group_create(request):
    return save_form(request, StudyGroupForm(request.POST or None), 'Создание учебной группы', 'Учебная группа создана.', 'group_list')


@role_required('admin')
def group_edit(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    return save_form(request, StudyGroupForm(request.POST or None, instance=group), 'Редактирование учебной группы', 'Учебная группа обновлена.', 'group_list')


@role_required('admin')
def group_delete(request, pk):
    return delete_object(request, get_object_or_404(StudyGroup, pk=pk), 'Удаление учебной группы', 'Учебная группа удалена.', 'group_list')


@role_required('admin')
def subject_list(request):
    return render(request, 'journal/subject_list.html', {'subjects': Subject.objects.all()})


@role_required('admin')
def subject_create(request):
    return save_form(request, SubjectForm(request.POST or None), 'Создание учебного предмета', 'Учебный предмет создан.', 'subject_list')


@role_required('admin')
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    return save_form(request, SubjectForm(request.POST or None, instance=subject), 'Редактирование учебного предмета', 'Учебный предмет обновлен.', 'subject_list')


@role_required('admin')
def subject_delete(request, pk):
    return delete_object(request, get_object_or_404(Subject, pk=pk), 'Удаление учебного предмета', 'Учебный предмет удален.', 'subject_list')


@role_required('admin')
def assignment_list(request):
    assignments = TeacherAssignment.objects.select_related('teacher__user__profile', 'group', 'subject')
    return render(request, 'journal/assignment_list.html', {'assignments': assignments})


@role_required('admin')
def assignment_create(request):
    return save_form(request, TeacherAssignmentForm(request.POST or None), 'Назначение преподавателя', 'Назначение создано.', 'assignment_list')


@role_required('admin')
def assignment_delete(request, pk):
    return delete_object(request, get_object_or_404(TeacherAssignment, pk=pk), 'Удаление назначения', 'Назначение удалено.', 'assignment_list')


@login_required
def schedule_list(request):
    lessons = Lesson.objects.select_related('group', 'subject', 'teacher__user__profile')
    if is_teacher(request.user):
        lessons = lessons.filter(teacher=getattr(request.user, 'teacher_profile', None))
    elif is_student(request.user):
        student = getattr(request.user, 'student_profile', None)
        lessons = lessons.filter(group=student.group) if student else lessons.none()
    if request.GET.get('date_from'):
        lessons = lessons.filter(date__gte=request.GET['date_from'])
    if request.GET.get('date_to'):
        lessons = lessons.filter(date__lte=request.GET['date_to'])
    return render(request, 'journal/schedule_list.html', {'lessons': lessons.order_by('date', 'start_time')})


@role_required('admin')
def lesson_create(request):
    return save_form(request, LessonForm(request.POST or None), 'Создание расписания занятия', 'Занятие добавлено в расписание.', 'schedule_list')


@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('group', 'subject', 'teacher__user__profile'), pk=pk)
    if not teacher_can_access_lesson(request.user, lesson):
        messages.error(request, 'Нет доступа к занятию.')
        return redirect('schedule_list')
    student = getattr(request.user, 'student_profile', None)
    return render(request, 'journal/lesson_detail.html', {
        'lesson': lesson,
        'grade': Grade.objects.filter(lesson=lesson, student=student).first() if student else None,
        'attendance': Attendance.objects.filter(lesson=lesson, student=student).first() if student else None,
    })


@login_required
def lesson_edit(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related('group', 'subject', 'teacher__user__profile'), pk=pk)
    if is_student(request.user) or not teacher_can_access_lesson(request.user, lesson):
        messages.error(request, 'Нет прав на редактирование занятия.')
        return redirect('schedule_list')

    form_class = LessonForm if is_admin(request.user) else TeacherLessonEditForm
    form = form_class(request.POST or None, instance=lesson)
    students = lesson.group.students.select_related('user__profile')

    if request.method == 'POST' and form.is_valid():
        lesson = form.save()
        save_lesson_marks(request, lesson, students)
        messages.success(request, 'Занятие обновлено.')
        return redirect('lesson_edit', pk=lesson.pk)

    return render(request, 'journal/lesson_edit.html', {
        'form': form,
        'lesson': lesson,
        'students': students,
        'existing_grades': {g.student_id: g for g in Grade.objects.filter(lesson=lesson)},
        'existing_attendance': {a.student_id: a for a in Attendance.objects.filter(lesson=lesson)},
        'attendance_choices': Attendance.STATUS_CHOICES,
    })


def save_lesson_marks(request, lesson, students):
    for student in students:
        value = request.POST.get(f'grade_{student.id}', '').strip()
        status = request.POST.get(f'attendance_{student.id}', '').strip()

        if value:
            try:
                value = int(value)
                if 2 <= value <= 5:
                    Grade.objects.update_or_create(lesson=lesson, student=student, defaults={'value': value})
                else:
                    messages.warning(request, f'Оценка для {student} должна быть от 2 до 5.')
            except ValueError:
                messages.warning(request, f'Оценка для {student} должна быть числом.')
        else:
            Grade.objects.filter(lesson=lesson, student=student).delete()

        if status:
            Attendance.objects.update_or_create(lesson=lesson, student=student, defaults={'status': status})


@role_required('admin')
def lesson_delete(request, pk):
    return delete_object(request, get_object_or_404(Lesson, pk=pk), 'Удаление занятия', 'Занятие удалено из расписания.', 'schedule_list')


@login_required
def final_grade_list(request):
    grades = FinalGrade.objects.select_related('student__user__profile', 'subject')
    if is_teacher(request.user):
        grades = grades.filter(student__group__assignments__teacher=request.user.teacher_profile).distinct()
    elif is_student(request.user):
        grades = grades.filter(student=getattr(request.user, 'student_profile', None))
    return render(request, 'journal/final_grade_list.html', {'grades': grades})


@role_required('admin', 'teacher')
def final_grade_create(request):
    form = FinalGradeForm(request.POST or None)
    if is_teacher(request.user):
        teacher = request.user.teacher_profile
        form.fields['student'].queryset = Student.objects.filter(group__assignments__teacher=teacher).distinct()
        form.fields['subject'].queryset = Subject.objects.filter(assignments__teacher=teacher).distinct()

    if request.method == 'POST' and form.is_valid():
        grade = form.save(commit=False)
        if is_teacher(request.user) and not teacher_can_access_student(request.user, grade.student):
            messages.error(request, 'Нет доступа к выбранному обучающемуся.')
            return redirect('final_grade_list')
        grade.save()
        messages.success(request, 'Итоговая оценка сохранена.')
        return redirect('final_grade_list')
    return render(request, 'journal/form.html', {'form': form, 'title': 'Итоговая оценка'})


@role_required('admin', 'teacher')
def final_grade_edit(request, pk):
    grade = get_object_or_404(FinalGrade, pk=pk)
    if is_teacher(request.user) and not teacher_can_access_student(request.user, grade.student):
        messages.error(request, 'Нет доступа к итоговой оценке.')
        return redirect('final_grade_list')
    return save_form(request, FinalGradeForm(request.POST or None, instance=grade), 'Редактирование итоговой оценки', 'Итоговая оценка обновлена.', 'final_grade_list')


@role_required('admin', 'teacher')
def final_grade_delete(request, pk):
    grade = get_object_or_404(FinalGrade, pk=pk)
    if is_teacher(request.user) and not teacher_can_access_student(request.user, grade.student):
        messages.error(request, 'Нет доступа к итоговой оценке.')
        return redirect('final_grade_list')
    return delete_object(request, grade, 'Удаление итоговой оценки', 'Итоговая оценка удалена.', 'final_grade_list')


@login_required
def reports_index(request):
    return render(request, 'journal/reports_index.html')


@role_required('admin')
def report_activity(request):
    form = ReportFilterForm(request.GET or None)
    rows = []
    if form.is_valid():
        rows = journal_activity_report(
            date_from=form.cleaned_data.get('date_from'),
            date_to=form.cleaned_data.get('date_to'),
            subject=form.cleaned_data.get('subject'),
            teacher=form.cleaned_data.get('teacher'),
            group=form.cleaned_data.get('group'),
        )
    return render(request, 'journal/report_activity.html', {'form': form, 'rows': rows})


@login_required
def report_student(request):
    form = ReportFilterForm(request.GET or None)
    rows, averages, selected_student = [], [], None
    if form.is_valid():
        selected_student = selected_student_for_report(request.user, form)
        if selected_student and teacher_can_access_student(request.user, selected_student):
            rows, averages = student_current_report(
                selected_student,
                date_from=form.cleaned_data.get('date_from'),
                date_to=form.cleaned_data.get('date_to'),
                subject=form.cleaned_data.get('subject'),
            )
        elif selected_student:
            messages.error(request, 'Нет доступа к данным выбранного обучающегося.')
    return render(request, 'journal/report_student.html', {'form': form, 'rows': rows, 'averages': averages, 'selected_student': selected_student})


@role_required('admin', 'teacher')
def report_subject_group(request):
    form = ReportFilterForm(request.GET or None)
    teacher_limited_form(form, request.user)
    data = None
    if form.is_valid() and form.cleaned_data.get('group') and form.cleaned_data.get('subject'):
        students, lessons, grade_map, _, averages = subject_group_report(
            form.cleaned_data['group'],
            form.cleaned_data['subject'],
            date_from=form.cleaned_data.get('date_from'),
            date_to=form.cleaned_data.get('date_to'),
        )
        data = {
            'lessons': lessons,
            'rows': [{'student': st, 'cells': [grade_map.get(st.id, {}).get(lesson.id) for lesson in lessons], 'average': averages.get(st.id)} for st in students],
        }
    return render(request, 'journal/report_subject_group.html', {'form': form, 'data': data})


@role_required('admin', 'teacher')
def report_performance_statistics(request):
    form = ReportFilterForm(request.GET or None)
    teacher = teacher_limited_form(form, request.user)
    rows = []
    if form.is_valid():
        rows = performance_statistics(
            group=form.cleaned_data.get('group'),
            subject=form.cleaned_data.get('subject'),
            date_from=form.cleaned_data.get('date_from'),
            date_to=form.cleaned_data.get('date_to'),
            threshold=form.cleaned_data.get('threshold') or 3.0,
            teacher=teacher or form.cleaned_data.get('teacher'),
        )
    return render(request, 'journal/report_performance.html', {'form': form, 'rows': rows})


@role_required('admin', 'teacher')
def report_attendance_statistics(request):
    form = ReportFilterForm(request.GET or None)
    teacher = teacher_limited_form(form, request.user)
    result = None
    if form.is_valid():
        result = attendance_statistics(
            group=form.cleaned_data.get('group'),
            subject=form.cleaned_data.get('subject'),
            date_from=form.cleaned_data.get('date_from'),
            date_to=form.cleaned_data.get('date_to'),
            teacher=teacher or form.cleaned_data.get('teacher'),
        )
    return render(request, 'journal/report_attendance.html', {'form': form, 'result': result})


@login_required
def report_final_statement(request):
    form = ReportFilterForm(request.GET or None)
    rows, selected_student = [], None
    if form.is_valid():
        selected_student = selected_student_for_report(request.user, form)
        if selected_student and teacher_can_access_student(request.user, selected_student):
            rows = final_statement(selected_student)
        elif selected_student:
            messages.error(request, 'Нет доступа к итоговой ведомости выбранного обучающегося.')
    return render(request, 'journal/report_final.html', {'form': form, 'rows': rows, 'selected_student': selected_student})
