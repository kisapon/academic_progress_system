from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_TEACHER = 'teacher'
    ROLE_STUDENT = 'student'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Администрация'),
        (ROLE_TEACHER, 'Преподаватель'),
        (ROLE_STUDENT, 'Обучающийся'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES)
    middle_name = models.CharField('Отчество', max_length=150, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_role_display()})'

    @property
    def full_name(self):
        parts = [self.user.last_name, self.user.first_name, self.middle_name]
        return ' '.join([p for p in parts if p]) or self.user.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    position = models.CharField('Должность', max_length=120, blank=True, default='Преподаватель')

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'

    def __str__(self):
        profile = getattr(self.user, 'profile', None)
        return profile.full_name if profile else self.user.get_full_name() or self.user.username


class Subject(models.Model):
    name = models.CharField('Название предмета', max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Учебный предмет'
        verbose_name_plural = 'Учебные предметы'

    def __str__(self):
        return self.name


class StudyGroup(models.Model):
    number = models.CharField('Номер группы', max_length=50, unique=True)
    specialization = models.CharField('Профиль/специализация', max_length=200, blank=True)
    study_year = models.PositiveIntegerField('Учебный год', default=timezone.now().year)
    curator = models.ForeignKey(
        Teacher,
        verbose_name='Руководитель группы',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='curated_groups',
    )

    class Meta:
        ordering = ['number']
        verbose_name = 'Учебная группа'
        verbose_name_plural = 'Учебные группы'

    def __str__(self):
        return self.number


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    group = models.ForeignKey(StudyGroup, verbose_name='Учебная группа', on_delete=models.PROTECT, related_name='students')

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = 'Обучающийся'
        verbose_name_plural = 'Обучающиеся'

    def __str__(self):
        profile = getattr(self.user, 'profile', None)
        return profile.full_name if profile else self.user.get_full_name() or self.user.username


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(Teacher, verbose_name='Преподаватель', on_delete=models.CASCADE, related_name='assignments')
    group = models.ForeignKey(StudyGroup, verbose_name='Учебная группа', on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey(Subject, verbose_name='Предмет', on_delete=models.CASCADE, related_name='assignments')

    class Meta:
        unique_together = ('teacher', 'group', 'subject')
        verbose_name = 'Назначение преподавателя'
        verbose_name_plural = 'Назначения преподавателей'

    def __str__(self):
        return f'{self.teacher} — {self.group} — {self.subject}'


class Lesson(models.Model):
    LECTURE = 'lecture'
    PRACTICE = 'practice'
    CONTROL = 'control'
    LAB = 'lab'
    LESSON_TYPE_CHOICES = [
        (LECTURE, 'Лекция'),
        (PRACTICE, 'Практическое занятие'),
        (CONTROL, 'Контрольная работа'),
        (LAB, 'Лабораторная работа'),
    ]

    date = models.DateField('Дата занятия')
    start_time = models.TimeField('Время начала')
    end_time = models.TimeField('Время окончания')
    group = models.ForeignKey(StudyGroup, verbose_name='Учебная группа', on_delete=models.CASCADE, related_name='lessons')
    subject = models.ForeignKey(Subject, verbose_name='Предмет', on_delete=models.PROTECT, related_name='lessons')
    teacher = models.ForeignKey(Teacher, verbose_name='Преподаватель', on_delete=models.PROTECT, related_name='lessons')
    classroom = models.CharField('Аудитория', max_length=50, blank=True)
    lesson_type = models.CharField('Тип занятия', max_length=20, choices=LESSON_TYPE_CHOICES, default=PRACTICE)
    topic = models.CharField('Тема занятия', max_length=250, blank=True)
    homework = models.TextField('Домашнее задание', blank=True)

    class Meta:
        ordering = ['-date', 'start_time']
        unique_together = ('date', 'start_time', 'group', 'subject')
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'

    def __str__(self):
        return f'{self.date} {self.start_time} {self.group} {self.subject}'

    @property
    def is_filled(self):
        return bool(self.topic or self.homework or self.grades.exists() or self.attendances.exists())


class Grade(models.Model):
    lesson = models.ForeignKey(Lesson, verbose_name='Занятие', on_delete=models.CASCADE, related_name='grades')
    student = models.ForeignKey(Student, verbose_name='Обучающийся', on_delete=models.CASCADE, related_name='grades')
    value = models.PositiveSmallIntegerField('Оценка', validators=[MinValueValidator(2), MaxValueValidator(5)])
    comment = models.CharField('Комментарий', max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lesson', 'student')
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'

    def __str__(self):
        return f'{self.student}: {self.value} за {self.lesson}'


class Attendance(models.Model):
    PRESENT = 'present'
    EXCUSED = 'excused'
    UNEXCUSED = 'unexcused'
    LATE = 'late'
    STATUS_CHOICES = [
        (PRESENT, 'Присутствовал'),
        (EXCUSED, 'Отсутствовал по уважительной причине'),
        (UNEXCUSED, 'Отсутствовал без уважительной причины'),
        (LATE, 'Опоздал'),
    ]

    lesson = models.ForeignKey(Lesson, verbose_name='Занятие', on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, verbose_name='Обучающийся', on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField('Статус посещения', max_length=20, choices=STATUS_CHOICES, default=PRESENT)

    class Meta:
        unique_together = ('lesson', 'student')
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'

    def __str__(self):
        return f'{self.student}: {self.get_status_display()} за {self.lesson}'


class FinalGrade(models.Model):
    student = models.ForeignKey(Student, verbose_name='Обучающийся', on_delete=models.CASCADE, related_name='final_grades')
    subject = models.ForeignKey(Subject, verbose_name='Предмет', on_delete=models.CASCADE, related_name='final_grades')
    period = models.CharField('Период', max_length=100, default='Учебный год')
    value = models.PositiveSmallIntegerField('Итоговая оценка', validators=[MinValueValidator(2), MaxValueValidator(5)])

    class Meta:
        unique_together = ('student', 'subject', 'period')
        ordering = ['subject__name']
        verbose_name = 'Итоговая оценка'
        verbose_name_plural = 'Итоговые оценки'

    def __str__(self):
        return f'{self.student} — {self.subject}: {self.value}'
