from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import FinalGrade, Lesson, Profile, Student, StudyGroup, Subject, Teacher, TeacherAssignment


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


DATE_WIDGET = DateInput()
TIME_WIDGET = TimeInput()


def sync_user_role(user, data):
    """Создает/обновляет профиль и связанную запись роли пользователя."""
    role = data['role']
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.middle_name = data.get('middle_name', '')
    profile.birth_date = data.get('birth_date')
    profile.phone = data.get('phone', '')
    profile.save()

    if role == Profile.ROLE_TEACHER:
        Teacher.objects.get_or_create(user=user)
        Student.objects.filter(user=user).delete()
    elif role == Profile.ROLE_STUDENT:
        Student.objects.update_or_create(user=user, defaults={'group': data['group']})
        Teacher.objects.filter(user=user).delete()
    else:
        Teacher.objects.filter(user=user).delete()
        Student.objects.filter(user=user).delete()


class UserFieldsMixin(forms.Form):
    role = forms.ChoiceField(label='Роль', choices=Profile.ROLE_CHOICES)
    last_name = forms.CharField(label='Фамилия', max_length=150)
    first_name = forms.CharField(label='Имя', max_length=150)
    middle_name = forms.CharField(label='Отчество', max_length=150, required=False)
    birth_date = forms.DateField(label='Дата рождения', required=False, widget=DATE_WIDGET)
    phone = forms.CharField(label='Телефон', max_length=30, required=False)
    group = forms.ModelChoiceField(label='Учебная группа для обучающегося', queryset=StudyGroup.objects.all(), required=False)

    user_fields = ['username', 'last_name', 'first_name', 'middle_name', 'birth_date', 'phone', 'role', 'group']

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('role') == Profile.ROLE_STUDENT and not cleaned.get('group'):
            self.add_error('group', 'Для обучающегося необходимо выбрать учебную группу.')
        return cleaned

    def fill_user(self, user):
        user.last_name = self.cleaned_data['last_name']
        user.first_name = self.cleaned_data['first_name']
        user.is_staff = self.cleaned_data['role'] == Profile.ROLE_ADMIN
        return user


class UserCreateForm(UserFieldsMixin, UserCreationForm):
    class Meta:
        model = User
        fields = UserFieldsMixin.user_fields + ['password1', 'password2']

    def save(self, commit=True):
        user = self.fill_user(super().save(commit=False))
        if commit:
            user.save()
            sync_user_role(user, self.cleaned_data)
        return user


class UserUpdateForm(UserFieldsMixin, forms.ModelForm):
    password = forms.CharField(label='Новый пароль', required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = UserFieldsMixin.user_fields + ['password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        student = getattr(self.instance, 'student_profile', None)
        self.fields['role'].initial = profile.role if profile else Profile.ROLE_STUDENT
        self.fields['middle_name'].initial = profile.middle_name if profile else ''
        self.fields['birth_date'].initial = profile.birth_date if profile else None
        self.fields['phone'].initial = profile.phone if profile else ''
        self.fields['group'].initial = student.group if student else None

    def save(self, commit=True):
        user = self.fill_user(super().save(commit=False))
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            sync_user_role(user, self.cleaned_data)
        return user


class StudyGroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['number', 'specialization', 'study_year', 'curator']


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']


class TeacherAssignmentForm(forms.ModelForm):
    class Meta:
        model = TeacherAssignment
        fields = ['teacher', 'group', 'subject']


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['date', 'start_time', 'end_time', 'group', 'subject', 'teacher', 'classroom', 'lesson_type', 'topic', 'homework']
        widgets = {'date': DATE_WIDGET, 'start_time': TIME_WIDGET, 'end_time': TIME_WIDGET, 'homework': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_time'), cleaned.get('end_time')
        if start and end and start >= end:
            self.add_error('end_time', 'Время окончания должно быть позже времени начала.')
        return cleaned


class TeacherLessonEditForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['topic', 'homework']
        widgets = {'homework': forms.Textarea(attrs={'rows': 4})}


class FinalGradeForm(forms.ModelForm):
    class Meta:
        model = FinalGrade
        fields = ['student', 'subject', 'period', 'value']


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(label='Дата начала', required=False, widget=DATE_WIDGET)
    date_to = forms.DateField(label='Дата окончания', required=False, widget=DATE_WIDGET)
    group = forms.ModelChoiceField(label='Учебная группа', queryset=StudyGroup.objects.all(), required=False)
    subject = forms.ModelChoiceField(label='Предмет', queryset=Subject.objects.all(), required=False)
    teacher = forms.ModelChoiceField(label='Преподаватель', queryset=Teacher.objects.all(), required=False)
    student = forms.ModelChoiceField(label='Обучающийся', queryset=Student.objects.all(), required=False)
    threshold = forms.FloatField(label='Пороговый балл', required=False, min_value=2, max_value=5, initial=3.0)
