from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

#------------------------------------------------------------

class Classroom(models.Model):
    name = models.CharField(max_length=255)
    class_code = models.CharField(max_length=20, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
#------------------------------------------------------------

class Enrollment(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

#------------------------------------------------------------

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    file = models.FileField(upload_to='announcements/', blank=True, null=True) 
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

#------------------------------------------------------------

class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to='assignments/', blank=True, null=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()

#------------------------------------------------------------

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.IntegerField(blank=True, null=True)

#------------------------------------------------------------

class Comment(models.Model):
    content = models.TextField()
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, null=True, blank=True)
    announcement = models.ForeignKey('Announcement', on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)  # Private comments visibility
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)  # For replies

    def __str__(self):
        return f"{self.created_by.username}: {self.content[:30]}"
    
#------------------------------------------------------------
    
class Invitation(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='invitations')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    sent_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation to {self.classroom.name} for {self.student.username}"
    
#------------------------------------------------------------

class Quiz(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    time_limit_minutes = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(300)]
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.classroom.name}"

    def save(self, *args, **kwargs):
        if not self.id and self.start_time:  # New quiz being created
            self.end_time = self.start_time + timezone.timedelta(minutes=self.time_limit_minutes)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    @property
    def has_ended(self):
        return timezone.now() > self.end_time
    
#------------------------------------------------------------


class Question(models.Model):
    QUESTION_TYPES = (
        ('MCQ', 'Multiple Choice Question'),
        ('TEXT', 'Text Answer'),
    )

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    points = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.question_text[:50]}... ({self.quiz.title})"
    
#------------------------------------------------------------


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.choice_text[:50]}... ({self.question})"
    
#------------------------------------------------------------


class QuizSubmission(models.Model):
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_submitted = models.BooleanField(default=False)
    total_score = models.FloatField(default=0.0)
    teacher_comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('quiz', 'student')  # One submission per student per quiz

    def __str__(self):
        return f"{self.student.username}'s submission for {self.quiz.title}"

    def get_score(self):
        """
        Returns the percentage score for this submission.
        It counts correct answers and calculates score based on total questions.
        """
        total_questions = self.quiz.questions.count()
        correct = self.answers.filter(is_correct=True).count()
        return round((correct / total_questions) * 100, 2) if total_questions > 0 else 0.0

    def calculate_score(self):
        """Calculate total score based on answers"""
        correct_answers = self.answers.filter(
            choice__is_correct=True
        ).count()
        total_questions = self.quiz.questions.count()
        self.total_score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        self.save()

#------------------------------------------------------------


class Answer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer for {self.question} by {self.submission.student.username}"
    
#------------------------------------------------------------

class DiscussionThread(models.Model):
    classroom = models.ForeignKey('Classroom', on_delete=models.CASCADE, related_name='threads')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-last_activity']
        unique_together = ['classroom', 'title']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:100]
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.classroom.name})"
    
#------------------------------------------------------------

class DiscussionMessage(models.Model):
    thread = models.ForeignKey(DiscussionThread, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
    
    @property
    def was_edited(self):
        return self.is_edited
    
    def save(self, *args, **kwargs):
        if self.pk:  # Only for updates
            self.is_edited = True
            self.edited_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.created_by.username}: {self.content[:30]}"
    
#------------------------------------------------------------

class MessageReaction(models.Model):
    REACTION_MAP = {
        'thumbs_up': '👍',
        'heart': '❤️',
        'laugh': '😂',
        'surprise': '😮',
        'sad': '😢',
        'fire': '🔥'
    }
    
    REVERSE_REACTION_MAP = {v: k for k, v in REACTION_MAP.items()}
    
    REACTION_CHOICES = [
        (k, v) for k, v in REACTION_MAP.items()
    ]
    
    message = models.ForeignKey(DiscussionMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        
    @property
    def emoji(self):
        return self.REACTION_MAP.get(self.reaction, '')
    
#------------------------------------------------------------