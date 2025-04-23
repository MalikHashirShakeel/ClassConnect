from django import forms
from .models import Classroom, Announcement, Assignment
from .models import Quiz, Question, Choice
from django.forms import inlineformset_factory

#------------------------------------------------------------

# Form to create a new classroom
class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'class_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'class_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
        }

#------------------------------------------------------------


# Form to join a classroom
class JoinClassroomForm(forms.Form):
    class_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple',
            'placeholder': 'Enter Class Code'
        }),
        label='Class Code'
    )

#------------------------------------------------------------


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'content': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple', 'rows': 4}),
            'file': forms.FileInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
        }

#------------------------------------------------------------

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'file', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple', 'rows': 4}),
            'file': forms.FileInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple', 'type': 'datetime-local'}),
        }

#------------------------------------------------------------

class QuizInfoForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea, required=False)
    time_limit_minutes = forms.IntegerField(min_value=1, max_value=300)
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    number_of_questions = forms.IntegerField(min_value=1, max_value=50, label="Number of Questions")

#------------------------------------------------------------

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'time_limit_minutes', 'start_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

#------------------------------------------------------------

class QuestionForm(forms.ModelForm):
    choice_1 = forms.CharField(label="Option 1", max_length=255)
    choice_2 = forms.CharField(label="Option 2", max_length=255)
    choice_3 = forms.CharField(label="Option 3", max_length=255)
    choice_4 = forms.CharField(label="Option 4", max_length=255)
    correct_choice = forms.ChoiceField(
        choices=[('1', 'Option 1'), ('2', 'Option 2'), ('3', 'Option 3'), ('4', 'Option 4')],
        label="Correct Option",
        widget=forms.RadioSelect
    )

    class Meta:
        model = Question
        fields = ['question_text', 'points']

#------------------------------------------------------------
        
class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct']

#------------------------------------------------------------

# Inline formsets
QuestionFormSet = inlineformset_factory(Quiz, Question, form=QuestionForm, extra=1, can_delete=False)
ChoiceFormSet = inlineformset_factory(Question, Choice, form=ChoiceForm, extra=4, can_delete=False)
