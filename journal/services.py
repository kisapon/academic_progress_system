from collections import defaultdict
from statistics import mean

from .models import Attendance, FinalGrade, Grade, Lesson, Student, Subject


def avg(values):
    values = list(values)
    return round(mean(values), 2) if values else None


def percent(part, total):
    return round(part / total * 100, 1) if total else 0


def filter_lessons(date_from=None, date_to=None, group=None, subject=None, teacher=None):
    lessons = Lesson.objects.select_related('teacher__user__profile', 'group', 'subject')
    filters = {
        'date__gte': date_from,
        'date__lte': date_to,
        'group': group,
        'subject': subject,
        'teacher': teacher,
    }
    return lessons.filter(**{key: value for key, value in filters.items() if value})


def journal_activity_report(**filters):
    grouped = defaultdict(lambda: {'total': 0, 'filled': 0, 'empty': 0})
    for lesson in filter_lessons(**filters):
        data = grouped[(lesson.teacher, lesson.subject)]
        data['total'] += 1
        data['filled' if lesson.is_filled else 'empty'] += 1

    return [
        {'teacher': teacher, 'subject': subject, **data, 'percent': percent(data['filled'], data['total'])}
        for (teacher, subject), data in grouped.items()
    ]


def student_current_report(student, date_from=None, date_to=None, subject=None):
    lessons = filter_lessons(date_from, date_to, student.group, subject).order_by('date', 'start_time')
    grades = {g.lesson_id: g for g in Grade.objects.filter(student=student, lesson__in=lessons)}
    attendance = {a.lesson_id: a for a in Attendance.objects.filter(student=student, lesson__in=lessons)}
    values_by_subject = defaultdict(list)
    rows = []

    for lesson in lessons:
        grade = grades.get(lesson.id)
        if grade:
            values_by_subject[lesson.subject.name].append(grade.value)
        rows.append({'lesson': lesson, 'grade': grade, 'attendance': attendance.get(lesson.id)})

    averages = [{'subject': subject_name, 'avg': avg(values)} for subject_name, values in values_by_subject.items()]
    return rows, averages


def subject_group_report(group, subject, date_from=None, date_to=None):
    lessons = filter_lessons(date_from, date_to, group, subject).order_by('date', 'start_time')
    students = group.students.select_related('user__profile')
    grade_map = defaultdict(dict)
    attendance_map = defaultdict(dict)

    for grade in Grade.objects.filter(lesson__in=lessons, student__in=students):
        grade_map[grade.student_id][grade.lesson_id] = grade.value
    for mark in Attendance.objects.filter(lesson__in=lessons, student__in=students):
        attendance_map[mark.student_id][mark.lesson_id] = mark.get_status_display()

    averages = {student.id: avg(grade_map[student.id].values()) for student in students}
    return students, lessons, grade_map, attendance_map, averages


def performance_statistics(group=None, subject=None, date_from=None, date_to=None, threshold=3.0, teacher=None):
    lessons = filter_lessons(date_from, date_to, group, subject, teacher).order_by('date')
    lesson_dates = list(lessons.values_list('date', flat=True))
    if not lesson_dates:
        return []

    mid_date = lesson_dates[len(lesson_dates) // 2]
    students = Student.objects.select_related('user__profile', 'group')
    if group:
        students = students.filter(group=group)
    elif teacher:
        students = students.filter(group__assignments__teacher=teacher).distinct()

    subjects = Subject.objects.filter(id=subject.id) if subject else Subject.objects.all()
    rows = []
    for student in students:
        for subj in subjects:
            student_lessons = lessons.filter(group=student.group, subject=subj)
            avg_start = avg(Grade.objects.filter(student=student, lesson__in=student_lessons.filter(date__lte=mid_date)).values_list('value', flat=True))
            avg_end = avg(Grade.objects.filter(student=student, lesson__in=student_lessons.filter(date__gt=mid_date)).values_list('value', flat=True))
            if avg_start is None and avg_end is None:
                continue
            change = round((avg_end - avg_start) / avg_start * 100, 1) if avg_start and avg_end else None
            rows.append({
                'student': student,
                'subject': subj,
                'avg_start': avg_start,
                'avg_end': avg_end,
                'change': change,
                'is_low': (avg_end or avg_start or 0) < threshold,
            })
    return rows


def attendance_statistics(group=None, subject=None, date_from=None, date_to=None, teacher=None):
    lessons = filter_lessons(date_from, date_to, group, subject, teacher)
    records = Attendance.objects.filter(lesson__in=lessons)
    total = records.count()

    rows = []
    for subj in Subject.objects.filter(lessons__in=lessons).distinct():
        subject_records = records.filter(lesson__subject=subj)
        rows.append({
            'subject': subj,
            'excused': subject_records.filter(status=Attendance.EXCUSED).count(),
            'unexcused': subject_records.filter(status=Attendance.UNEXCUSED).count(),
            'late': subject_records.filter(status=Attendance.LATE).count(),
        })

    return {
        'rows': rows,
        'total_records': total,
        'percent_excused': percent(records.filter(status=Attendance.EXCUSED).count(), total),
        'percent_unexcused': percent(records.filter(status=Attendance.UNEXCUSED).count(), total),
    }


def final_statement(student):
    return FinalGrade.objects.filter(student=student).select_related('subject').order_by('subject__name')
