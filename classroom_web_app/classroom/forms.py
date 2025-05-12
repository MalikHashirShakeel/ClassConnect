from django import forms
from .models import Classroom, Announcement, Assignment
from .models import Quiz, Question, Choice, DiscussionThread, DiscussionMessage
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import timezone
import datetime

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
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple',
                'rows': 4}),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple'}),
            'due_date': forms.TextInput(attrs={  # <-- change to TextInput for JS compatibility
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-purple',
                'placeholder': 'Select date and time'
            }),
        }

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        now = timezone.now()

        if not due_date:
            raise forms.ValidationError("Please enter a valid due date and time.")

        if due_date <= now:
            raise forms.ValidationError("Due date must be in the future.")

        if due_date > now + datetime.timedelta(days=365):
            raise forms.ValidationError("Due date can't be more than 1 year from now.")

        return due_date

#------------------------------------------------------------

class QuizInfoForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        label="Quiz Title",
        help_text="Enter a concise and clear quiz title (max 255 characters)."
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label="Quiz Description",
        help_text="(Optional) Describe what the quiz is about."
    )
    time_limit_minutes = forms.IntegerField(
        min_value=1,
        max_value=300,
        label="Time Limit (in minutes)",
        help_text="Set the quiz duration (1 - 300 minutes)."
    )
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Quiz Start Time",
        help_text="Select when the quiz will start (future only)."
    )
    number_of_questions = forms.IntegerField(
        min_value=1,
        max_value=50,
        label="Number of Questions",
        help_text="Set how many questions the quiz will have (1 - 50)."
    )

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if start_time < timezone.now():
            raise ValidationError("Start time must be in the future.")
        return start_time

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
    choice_1 = forms.CharField(label="Option 1", max_length=255, required=True)
    choice_2 = forms.CharField(label="Option 2", max_length=255, required=True)
    choice_3 = forms.CharField(label="Option 3", max_length=255, required=True)
    choice_4 = forms.CharField(label="Option 4", max_length=255, required=True)

    correct_choice = forms.ChoiceField(
        choices=[
            ('1', 'Option 1'),
            ('2', 'Option 2'),
            ('3', 'Option 3'),
            ('4', 'Option 4')
        ],
        label="Correct Option",
        widget=forms.RadioSelect
    )

    class Meta:
        model = Question
        fields = ['question_text', 'points']
        labels = {
            'question_text': 'Question Text',
            'points': 'Points (1–100)'
        }
        help_texts = {
            'points': 'Each question can carry 1 to 100 points.'
        }

    def clean(self):
        cleaned_data = super().clean()
        question_text = cleaned_data.get('question_text')
        points = cleaned_data.get('points')

        if not question_text:
            raise ValidationError("Question text cannot be empty.")

        if points is not None and (points < 1 or points > 100):
            raise ValidationError("Points must be between 1 and 100.")

        return cleaned_data

#------------------------------------------------------------
        
class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct']

#------------------------------------------------------------

class DiscussionThreadForm(forms.ModelForm):
    class Meta:
        model = DiscussionThread
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Enter thread title...'
            }),
        }

#------------------------------------------------------------

class DiscussionMessageForm(forms.ModelForm):
    class Meta:
        model = DiscussionMessage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500',
                'rows': 3,
                'placeholder': 'Write your message here...'
            }),
        }

#------------------------------------------------------------

# Inline formsets
QuestionFormSet = inlineformset_factory(Quiz, Question, form=QuestionForm, extra=1, can_delete=False)
ChoiceFormSet = inlineformset_factory(Question, Choice, form=ChoiceForm, extra=4, can_delete=False)
