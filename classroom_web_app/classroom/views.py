from .models import Classroom, Enrollment, Announcement, Assignment, Submission, Comment, Invitation, Choice, Quiz, QuizSubmission, Answer, Question, DiscussionThread, DiscussionMessage, MessageReaction
from .forms import ClassroomForm, AnnouncementForm, AssignmentForm, QuestionForm, QuizInfoForm, DiscussionThreadForm, DiscussionMessageForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import is_naive, make_aware
from django.views.decorators.csrf import csrf_exempt
from django.forms import formset_factory
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Avg, Max, Min
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.db import IntegrityError
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from users.models import EmailVerificationCode
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
import random
import json
import csv
import re
import io


#------------------------------------------------------------

@login_required
def classroom_list(request):
    """Display classrooms created by the user and classrooms the user is enrolled in."""
    created_classrooms = Classroom.objects.filter(created_by=request.user)
    enrolled_classrooms = Classroom.objects.filter(enrollment__student=request.user)

    context = {
        'created_classrooms': created_classrooms,
        'enrolled_classrooms': enrolled_classrooms,
    }
    return render(request, 'classroom/classroom_list.html', context)

#------------------------------------------------------------

@login_required
def create_classroom(request):
    """View to create a new classroom."""
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.created_by = request.user
            classroom.save()
            messages.success(request, 'Classroom created successfully!')
            return redirect('classroom_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClassroomForm()

    context = {
        'form': form,
    }
    return render(request, 'classroom/create_classroom.html', context)

#------------------------------------------------------------

@login_required
def join_classroom(request):
    """View to join a classroom using a class code."""
    if request.method == 'POST':
        class_code = request.POST.get('class_code', '').strip()
        if not class_code:
            messages.error(request, 'Please enter a class code.')
            return render(request, 'classroom/join_classroom.html')

        try:
            classroom = Classroom.objects.get(class_code=class_code)

            # ⛔ Prevent joining own classroom
            if classroom.created_by == request.user:
                messages.warning(request, 'You cannot join a classroom you created.')
                return redirect('classroom_list')

            # ✅ Proceed with enrollment
            if not Enrollment.objects.filter(classroom=classroom, student=request.user).exists():
                Enrollment.objects.create(classroom=classroom, student=request.user)
                messages.success(request, f'You have successfully joined {classroom.name}!')
            else:
                messages.warning(request, 'You are already enrolled in this classroom.')

            return redirect('classroom_list')

        except Classroom.DoesNotExist:
            messages.error(request, 'Invalid class code. Please try again.')

    return render(request, 'classroom/join_classroom.html')

#-------------------------------------------------------------

def classroom_detail(request, classroom_id):
    """View to display classroom details and pending/missed tasks for students."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    is_creator = classroom.created_by == request.user

    # Check if user is authorized
    if not is_creator and not Enrollment.objects.filter(classroom=classroom, student=request.user).exists():
        messages.error(request, 'You are not enrolled in this classroom.')
        return redirect('classroom_list')

    # Get all announcements and assignments for the classroom
    announcements = Announcement.objects.filter(classroom=classroom).order_by('-created_at')
    assignments = Assignment.objects.filter(classroom=classroom).order_by('-created_at')
    quizzes = Quiz.objects.filter(classroom=classroom).order_by('-start_time')

    # For students, calculate pending and missed tasks
    pending_tasks = []
    missed_tasks = []
    if not is_creator:
        now = timezone.now()
        
        # Check assignments
        for assignment in assignments:
            # Check if student has already submitted this assignment
            submitted = Submission.objects.filter(assignment=assignment, student=request.user).exists()
            if not submitted:
                if assignment.due_date > now:
                    time_left = assignment.due_date - now
                    urgency = (
                        'red' if time_left <= timedelta(days=1) else
                        'orange' if time_left <= timedelta(days=3) else
                        'green'
                    )
                    pending_tasks.append({
                        'id': assignment.id,
                        'type': 'assignment',
                        'title': assignment.title,
                        'due_date': assignment.due_date,
                        'urgency': urgency,
                    })
                else:
                    missed_tasks.append({
                        'id': assignment.id,
                        'type': 'assignment',
                        'title': assignment.title,
                        'due_date': assignment.due_date,
                    })

        # Check quizzes
        for quiz in quizzes:
            # Check if student has already submitted this quiz
            submitted = QuizSubmission.objects.filter(quiz=quiz, student=request.user).exists()
            if not submitted:
                if quiz.end_time > now:
                    time_left = quiz.end_time - now
                    urgency = (
                        'red' if time_left <= timedelta(days=1) else
                        'orange' if time_left <= timedelta(days=3) else
                        'green'
                    )
                    pending_tasks.append({
                        'id': quiz.id,
                        'type': 'quiz',
                        'title': quiz.title,
                        'due_date': quiz.end_time,
                        'urgency': urgency,
                    })
                else:
                    missed_tasks.append({
                        'id': quiz.id,
                        'type': 'quiz',
                        'title': quiz.title,
                        'due_date': quiz.end_time,
                    })

    context = {
        'classroom': classroom,
        'is_creator': is_creator,
        'announcements': announcements,
        'assignments': assignments,
        'pending_tasks': pending_tasks,
        'missed_tasks': missed_tasks,
        'quizzes': quizzes,
    }
    return render(request, 'classroom/classroom_detail.html', context)

#------------------------------------------------------------

@login_required
def add_announcement(request, classroom_id):
    """View to add an announcement to a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if classroom.created_by != request.user:
        messages.error(request, 'Only the classroom creator can add announcements.')
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.classroom = classroom
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, 'Announcement added successfully!')
            return redirect('classroom_detail', classroom_id=classroom.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AnnouncementForm()

    context = {
        'form': form,
        'classroom': classroom,
    }
    return render(request, 'classroom/add_announcement.html', context)

#-------------------------------------------------------------

@login_required
def delete_announcement(request, announcement_id):
    """View to delete an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if announcement.created_by == request.user:
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
    else:
        messages.error(request, 'You are not allowed to delete this announcement.')

    return redirect('classroom_detail', classroom_id=announcement.classroom.id)

#-------------------------------------------------------------

@login_required
def add_assignment(request, classroom_id):
    """View to add an assignment to a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if classroom.created_by != request.user:
        messages.error(request, 'Only the classroom creator can add assignments.')
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.classroom = classroom
            assignment.created_by = request.user
            assignment.save()
            messages.success(request, 'Assignment added successfully!')
            return redirect('classroom_detail', classroom_id=classroom.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AssignmentForm()

    context = {
        'form': form,
        'classroom': classroom,
    }
    return render(request, 'classroom/add_assignment.html', context)

#-------------------------------------------------------------

@login_required
def delete_assignment(request, assignment_id):
    """View to delete an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if assignment.created_by == request.user:
        classroom_id = assignment.classroom.id if assignment.classroom else None
        assignment.delete()
        if classroom_id:
            messages.success(request, "Assignment deleted successfully.")
            return redirect('classroom_detail', classroom_id=classroom_id)
    messages.error(request, "You are not authorized to delete this assignment.")
    return redirect('classroom_list')  # fallback redirect if anything wrong

#------------------------------------------------------------

@login_required
def view_announcement(request, announcement_id):
    """View to display the full details of an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    is_creator = announcement.created_by == request.user if announcement.created_by else False

    absolute_file_url = request.build_absolute_uri(announcement.file.url) if announcement.file else None

    context = {
        'announcement': announcement,
        'is_creator': is_creator,
        'absolute_file_url': absolute_file_url,
    }
    return render(request, 'classroom/view_announcement.html', context)

#------------------------------------------------------------

@login_required
def edit_announcement(request, announcement_id):
    """View to edit an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if announcement.created_by != request.user:
        messages.error(request, "You are not authorized to edit this announcement.")
        return redirect('view_announcement', announcement_id=announcement.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated successfully.")
            return redirect('view_announcement', announcement_id=announcement.id)
        else:
            messages.error(request, "There was an error updating the announcement.")
    else:
        form = AnnouncementForm(instance=announcement)

    context = {
        'form': form,
        'announcement': announcement,
    }
    return render(request, 'classroom/edit_announcement.html', context)

#------------------------------------------------------------

@login_required
def view_assignment(request, assignment_id):
    """View to display the full details of an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    absolute_file_url = request.build_absolute_uri(assignment.file.url) if assignment.file else None
    is_creator = assignment.created_by == request.user if assignment.created_by else False
    is_due_date_passed = timezone.now() > assignment.due_date
    submission = Submission.objects.filter(assignment=assignment, student=request.user).first()

    context = {
        'assignment': assignment,
        'is_creator': is_creator,
        'is_due_date_passed': is_due_date_passed,
        'submission': submission,
        'absolute_file_url': absolute_file_url,
    }
    return render(request, 'classroom/view_assignment.html', context)

#------------------------------------------------------------

@login_required
def edit_assignment(request, assignment_id):
    """View to edit an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if assignment.created_by != request.user:
        messages.error(request, "You are not authorized to edit this assignment.")
        return redirect('view_assignment', assignment_id=assignment.id)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated successfully.")
            return redirect('view_assignment', assignment_id=assignment.id)
        else:
            messages.error(request, "There was an error updating the assignment.")
    else:
        form = AssignmentForm(instance=assignment)

    context = {
        'form': form,
        'assignment': assignment,
    }
    return render(request, 'classroom/edit_assignment.html', context)

#------------------------------------------------------------

@login_required
def submit_assignment(request, assignment_id):
    """View to submit an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            Submission.objects.create(
                assignment=assignment,
                student=request.user,
                file=file
            )
            messages.success(request, "Assignment submitted successfully.")
            return redirect('view_assignment', assignment_id=assignment.id)
        else:
            messages.error(request, "Please upload a file to submit.")
    return render(request, 'classroom/submit_assignment.html', {'assignment': assignment})

#------------------------------------------------------------

@login_required
def create_quiz_info(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to create a quiz for this classroom.")
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = QuizInfoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            data['start_time'] = data['start_time'].isoformat()
            request.session['quiz_info'] = data
            messages.success(request, "Quiz information saved successfully. Now add questions.")
            return redirect('create_quiz_questions', classroom_id=classroom_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = QuizInfoForm()

    return render(request, 'classroom/create_quiz_info.html', {
        'form': form,
        'classroom': classroom,
    })

#------------------------------------------------------------

@login_required
def create_quiz_questions(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to create a quiz for this classroom.")
        return redirect('classroom_detail', classroom_id=classroom_id)

    quiz_info = request.session.get('quiz_info')
    if not quiz_info:
        messages.error(request, "Quiz information is missing. Please provide quiz details first.")
        return redirect('create_quiz_info', classroom_id=classroom_id)

    quiz_info['start_time'] = datetime.fromisoformat(quiz_info['start_time'])

    start_time = quiz_info['start_time']
    if is_naive(start_time):
        start_time = make_aware(start_time)

    num_questions = int(quiz_info.get('number_of_questions', 1))
    QuestionFormSet = formset_factory(QuestionForm, extra=num_questions)

    if request.method == 'POST':
        formset = QuestionFormSet(request.POST)
        all_filled = True

        if formset.is_valid():
            for question_form in formset:
                # Check for required fields manually
                required_fields = ['question_text', 'points', 'choice_1', 'choice_2', 'choice_3', 'choice_4', 'correct_choice']
                if not question_form.cleaned_data or not all(field in question_form.cleaned_data and question_form.cleaned_data[field] for field in required_fields):
                    all_filled = False
                    break

            if not all_filled:
                messages.error(request, "All question fields must be filled out. Please complete every question.")
            else:
                quiz = Quiz.objects.create(
                    title=quiz_info['title'],
                    description=quiz_info['description'],
                    time_limit_minutes=quiz_info['time_limit_minutes'],
                    start_time=start_time,
                    end_time=start_time + timedelta(minutes=quiz_info['time_limit_minutes']),
                    classroom=classroom,
                    created_by=request.user,
                )

                for question_form in formset:
                    question = question_form.save(commit=False)
                    question.quiz = quiz
                    question.question_type = 'MCQ'
                    question.save()

                    choices = [
                        question_form.cleaned_data['choice_1'],
                        question_form.cleaned_data['choice_2'],
                        question_form.cleaned_data['choice_3'],
                        question_form.cleaned_data['choice_4'],
                    ]
                    correct_index = int(question_form.cleaned_data['correct_choice']) - 1

                    for i, choice_text in enumerate(choices):
                        Choice.objects.create(
                            question=question,
                            choice_text=choice_text,
                            is_correct=(i == correct_index)
                        )

                del request.session['quiz_info']
                messages.success(request, "Quiz created successfully!")
                return redirect('classroom_detail', classroom_id=classroom_id)

        else:
            messages.error(request, "Please correct the form errors.")
    else:
        formset = QuestionFormSet()

    return render(request, 'classroom/create_quiz_questions.html', {
        'formset': formset,
        'classroom': classroom,
    })

#------------------------------------------------------------

@login_required
def view_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    is_creator = quiz.created_by == request.user if quiz.created_by else False
    submission = None
    total_score = None

    if not is_creator:
        submission = QuizSubmission.objects.filter(quiz=quiz, student=request.user).first()
        if submission and submission.is_submitted:
            total_score = submission.total_score

    context = {
        'quiz': quiz,
        'is_creator': is_creator,
        'submission': submission,
        'total_score': total_score,
    }
    return render(request, 'classroom/view_quiz.html', context)

#------------------------------------------------------------

@login_required
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if not quiz.is_active:
        messages.error(request, "This quiz is not currently open.")
        return redirect('view_quiz', quiz_id=quiz.id)

    existing_submission = QuizSubmission.objects.filter(quiz=quiz, student=request.user).first()
    if existing_submission and existing_submission.is_submitted:
        messages.warning(request, "You have already submitted this quiz.")
        return redirect('view_quiz', quiz_id=quiz.id)

    if request.method == 'POST':
        submission = existing_submission or QuizSubmission.objects.create(
            quiz=quiz, student=request.user, is_submitted=True
        )

        total_score = 0
        total_points = 0
        missing_answers = False

        for question in quiz.questions.all():
            choice_id = request.POST.get(f"question_{question.id}")
            selected_choice = Choice.objects.filter(id=choice_id, question=question).first()

            if not selected_choice:
                missing_answers = True
                continue

            is_correct = selected_choice.is_correct
            if is_correct:
                total_score += question.points

            Answer.objects.create(
                submission=submission,
                question=question,
                choice=selected_choice,
                is_correct=is_correct
            )
            total_points += question.points

        submission.total_score = (total_score / total_points) * 100 if total_points else 0
        submission.is_submitted = True
        submission.save()

        if missing_answers:
            messages.warning(request, "Some questions were unanswered and marked incorrect.")

        messages.success(request, "Your quiz has been submitted!")
        return redirect('view_quiz', quiz_id=quiz.id)

    questions = quiz.questions.prefetch_related('choices')
    return render(request, 'classroom/submit_quiz.html', {
        'quiz': quiz,
        'questions': questions,
    })

#------------------------------------------------------------

@login_required
def view_quiz_submissions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if quiz.created_by != request.user:
        messages.error(request, "You are not authorized to view submissions for this quiz.")
        return redirect('classroom_detail', classroom_id=quiz.classroom.id)

    submissions = QuizSubmission.objects.filter(quiz=quiz)
    enrolled_students = User.objects.filter(enrollment__classroom=quiz.classroom)
    submitted_ids = submissions.values_list('student_id', flat=True)
    not_submitted = enrolled_students.exclude(id__in=submitted_ids)

    context = {
        'quiz': quiz,
        'submissions': submissions,
        'not_submitted_students': not_submitted,
    }
    return render(request, 'classroom/view_quiz_submissions.html', context)

#------------------------------------------------------------

@login_required
def grade_quiz_submission(request, submission_id):
    submission = get_object_or_404(QuizSubmission, id=submission_id)
    quiz = submission.quiz
    if request.user != quiz.created_by:
        messages.error(request, "You are not authorized to grade this submission.")
        return redirect('view_quiz', quiz_id=quiz.id)

    answers = submission.answers.select_related('question', 'choice')
    return render(request, 'classroom/grade_quiz_submission.html', {
        'submission': submission,
        'answers': answers,
    })

#------------------------------------------------------------

@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if quiz.created_by != request.user:
        messages.error(request, "You are not authorized to delete this quiz.")
        return redirect('view_quiz', quiz_id=quiz.id)

    if request.method == 'POST':
        classroom_id = quiz.classroom.id
        quiz.delete()
        messages.success(request, "Quiz deleted successfully.")
        return redirect('classroom_detail', classroom_id=classroom_id)

    return redirect('view_quiz', quiz.id)

#------------------------------------------------------------

@login_required
def edit_submission(request, submission_id):
    """View to edit a submission."""
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.student != request.user:
        messages.error(request, "You are not authorized to edit this submission.")
        return redirect('view_assignment', assignment_id=submission.assignment.id)

    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            submission.file = file
            submission.save()
            messages.success(request, "Submission updated successfully.")
            return redirect('view_assignment', assignment_id=submission.assignment.id)
        else:
            messages.error(request, "Please upload a file to update your submission.")

    return render(request, 'classroom/edit_submission.html', {'submission': submission})

#------------------------------------------------------------

@login_required
def cancel_submission(request, submission_id):
    """View to cancel a submission."""
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.student != request.user:
        messages.error(request, "You are not authorized to cancel this submission.")
        return redirect('view_assignment', assignment_id=submission.assignment.id)

    submission.delete()
    messages.success(request, "Submission cancelled successfully.")
    return redirect('view_assignment', assignment_id=submission.assignment.id)

#------------------------------------------------------------

@login_required
def view_submissions(request, assignment_id):
    """View to display all submissions for an assignment and list students who haven't submitted."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if assignment.created_by != request.user:
        messages.error(request, "You are not authorized to view submissions for this assignment.")
        return redirect('view_assignment', assignment_id=assignment.id)
    
    submissions = Submission.objects.filter(assignment=assignment)
    enrolled_students = User.objects.filter(enrollment__classroom=assignment.classroom)
    submitted_students = submissions.values_list('student', flat=True)
    not_submitted_students = enrolled_students.exclude(id__in=submitted_students)

    context = {
        'assignment': assignment,
        'submissions': submissions,
        'not_submitted_students': not_submitted_students,
    }
    return render(request, 'classroom/view_submissions.html', context)

#------------------------------------------------------------

@login_required
def view_comments(request, object_type, object_id):
    if object_type == 'announcement':
        obj = get_object_or_404(Announcement, id=object_id)
        comments = Comment.objects.filter(announcement=obj, parent_comment__isnull=True)
    elif object_type == 'assignment':
        obj = get_object_or_404(Assignment, id=object_id)
        comments = Comment.objects.filter(assignment=obj, parent_comment__isnull=True)
    elif object_type == 'quiz':
        obj = get_object_or_404(Quiz, id=object_id)
        comments = Comment.objects.filter(quiz=obj, parent_comment__isnull=True)
    else:
        messages.error(request, "Invalid object type for comments.")
        return redirect('classroom_list')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(
                content=content,
                announcement=obj if object_type == 'announcement' else None,
                assignment=obj if object_type == 'assignment' else None,
                quiz=obj if object_type == 'quiz' else None,
                created_by=request.user
            )
            messages.success(request, "Comment posted successfully.")
        else:
            messages.error(request, "Comment cannot be empty.")
        return redirect('view_comments', object_type=object_type, object_id=object_id)

    return render(request, 'classroom/view_comments.html', {
        'object': obj,
        'comments': comments,
        'object_type': object_type,
    })

#------------------------------------------------------------

@login_required
def add_reply(request, comment_id):
    """View to add a reply to a comment."""
    parent_comment = get_object_or_404(Comment, id=comment_id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if content:
            Comment.objects.create(
                content=content,
                announcement=parent_comment.announcement,
                assignment=parent_comment.assignment,
                quiz=parent_comment.quiz,
                created_by=request.user,
                parent_comment=parent_comment
            )
            messages.success(request, "Reply added successfully.")
        else:
            messages.error(request, "Reply content cannot be empty.")

        if parent_comment.announcement:
            return redirect('view_comments', object_type='announcement', object_id=parent_comment.announcement.id)
        elif parent_comment.assignment:
            return redirect('view_comments', object_type='assignment', object_id=parent_comment.assignment.id)
        elif parent_comment.quiz:
            return redirect('view_comments', object_type='quiz', object_id=parent_comment.quiz.id)

    return redirect('classroom_list')

#------------------------------------------------------------

@login_required
def view_students(request, classroom_id):
    """View to display all students enrolled in a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to view students of this classroom.")
        return redirect('classroom_detail', classroom_id=classroom.id)

    enrollments = Enrollment.objects.filter(classroom=classroom)
    students = [enrollment.student for enrollment in enrollments]

    context = {
        'classroom': classroom,
        'students': students,
    }
    return render(request, 'classroom/view_students.html', context)

#------------------------------------------------------------

@login_required
def delete_student(request, classroom_id, student_id):
    """View to delete a student from the classroom and all their related data."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to remove students from this classroom.")
        return redirect('classroom_detail', classroom_id=classroom.id)

    student = get_object_or_404(User, id=student_id)

    Enrollment.objects.filter(classroom=classroom, student=student).delete()
    Comment.objects.filter(created_by=student, announcement__classroom=classroom).delete()
    Comment.objects.filter(created_by=student, assignment__classroom=classroom).delete()
    Submission.objects.filter(student=student, assignment__classroom=classroom).delete()

    messages.success(request, f"{student.username} has been removed from the classroom.")
    return redirect('view_students', classroom_id=classroom.id)

#-------------------------------------------------------------

@login_required
def add_student(request, classroom_id):
    """View to send an invitation to a student by email."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to add students to this classroom.")
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter a valid email address.')
        else:
            try:
                student = User.objects.get(email=email)
                if Enrollment.objects.filter(classroom=classroom, student=student).exists():
                    messages.warning(request, f'{student.username} is already enrolled.')
                elif Invitation.objects.filter(classroom=classroom, student=student, is_accepted=False).exists():
                    messages.warning(request, f'{student.username} has already been invited.')
                else:
                    Invitation.objects.create(
                        classroom=classroom,
                        student=student,
                        sent_by=request.user
                    )
                    messages.success(request, f'An invitation has been sent to {student.username}.')
            except User.DoesNotExist:
                messages.error(request, 'No user found with this email.')

    return render(request, 'classroom/add_student.html', {'classroom': classroom})

#------------------------------------------------------------

@login_required
def delete_classroom(request, classroom_id):
    """View to delete a classroom and all its related data."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if classroom.created_by != request.user:
        messages.error(request, "You are not authorized to delete this classroom.")
        return redirect('classroom_list')

    if request.method == 'POST':
        classroom.delete()
        messages.success(request, "Classroom deleted successfully.")
        return redirect('classroom_list')

    return redirect('classroom_detail', classroom_id=classroom.id)

#------------------------------------------------------------

@login_required
def leave_classroom(request, classroom_id):
    """View for a student to leave a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == 'POST':
        Enrollment.objects.filter(classroom=classroom, student=request.user).delete()
        messages.success(request, "You have left the classroom.")
        return redirect('classroom_list')

    return redirect('classroom_detail', classroom_id=classroom.id)

#------------------------------------------------------------

@login_required
def task_list(request):
    """View to display all pending and missed tasks from all classrooms."""
    enrolled_classrooms = Classroom.objects.filter(enrollment__student=request.user)
    assignments = Assignment.objects.filter(classroom__in=enrolled_classrooms).order_by('due_date')
    quizzes = Quiz.objects.filter(classroom__in=enrolled_classrooms).order_by('start_time')

    pending_tasks = []
    missed_tasks = []
    now = timezone.now()

    for assignment in assignments:
        # Check if student has submitted this assignment
        submitted = Submission.objects.filter(assignment=assignment, student=request.user).exists()
        if not submitted:
            if assignment.due_date > now:
                time_left = assignment.due_date - now
                urgency = (
                    'red' if time_left <= timedelta(days=1)
                    else 'orange' if time_left <= timedelta(days=3)
                    else 'green'
                )
                pending_tasks.append({
                    'id': assignment.id,
                    'type': 'assignment',
                    'title': assignment.title,
                    'due_date': assignment.due_date,
                    'urgency': urgency,
                    'classroom': assignment.classroom.name,
                })
            else:
                missed_tasks.append({
                    'id': assignment.id,
                    'type': 'assignment',
                    'title': assignment.title,
                    'due_date': assignment.due_date,
                    'classroom': assignment.classroom.name,
                })

    for quiz in quizzes:
        # Check if student has submitted this quiz
        submitted = QuizSubmission.objects.filter(quiz=quiz, student=request.user).exists()
        if not submitted:
            if quiz.end_time > now:
                time_left = quiz.end_time - now
                urgency = (
                    'red' if time_left <= timedelta(days=1)
                    else 'orange' if time_left <= timedelta(days=3)
                    else 'green'
                )
                pending_tasks.append({
                    'id': quiz.id,
                    'type': 'quiz',
                    'title': quiz.title,
                    'due_date': quiz.end_time,
                    'urgency': urgency,
                    'classroom': quiz.classroom.name,
                })
            else:
                missed_tasks.append({
                    'id': quiz.id,
                    'type': 'quiz',
                    'title': quiz.title,
                    'due_date': quiz.end_time,
                    'classroom': quiz.classroom.name,
                })

    if not pending_tasks and not missed_tasks:
        messages.info(request, "You have no pending or missed tasks.")

    context = {
        'pending_tasks': pending_tasks,
        'missed_tasks': missed_tasks,
    }
    return render(request, 'classroom/task_list.html', context)

#-------------------------------------------------------------

@login_required
def accept_invitation(request, invitation_id):
    """View to accept an invitation and join the classroom."""
    invitation = get_object_or_404(Invitation, id=invitation_id, student=request.user)
    if not invitation.is_accepted:
        try:
            Enrollment.objects.create(
                classroom=invitation.classroom,
                student=request.user,
                enrolled_at=timezone.now()
            )
            invitation.is_accepted = True
            invitation.save()
            messages.success(request, f'You have successfully joined {invitation.classroom.name}!')
        except Exception as e:
            messages.error(request, 'An error occurred while accepting the invitation. Please try again.')
    else:
        messages.warning(request, 'This invitation has already been accepted.')

    return redirect('classroom_list')

#-------------------------------------------------------------

@login_required
def invitations(request):
    """View to display pending invitations."""
    invitations = Invitation.objects.filter(student=request.user, is_accepted=False)

    if not invitations.exists():
        messages.info(request, "You have no pending invitations.")

    context = {
        'invitations': invitations,
    }
    return render(request, 'classroom/invitations.html', context)

#-------------------------------------------------------------

@login_required
def download_quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.user != quiz.classroom.created_by:
        messages.error(request, "You are not authorized to download quiz results.")
        return redirect('view_quiz', quiz_id=quiz.id)

    # Prepare CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{quiz.title}_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Marks'])

    enrolled_students = Enrollment.objects.filter(classroom=quiz.classroom).select_related('student')

    if not enrolled_students.exists():
        messages.warning(request, "No students found for this quiz.")
        return redirect('view_quiz', quiz_id=quiz.id)

    for enrollment in enrolled_students:
        student = enrollment.student
        submission = quiz.submissions.filter(student=student, is_submitted=True).first()
        
        if submission:
            try:
                score = submission.get_score()
            except Exception as e:
                score = 'N/A'
        else:
            score = 0  # No submission → 0 marks

        writer.writerow([
            student.get_full_name() or student.username,
            student.email,
            score
        ])

    return response

#-------------------------------------------------------------

def classconnect_features(request):
    return render(request, 'classroom/classconnect_features.html')

#-------------------------------------------------------------

@login_required
def quiz_analytics(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    classroom = quiz.classroom

    if request.user != classroom.created_by:
        messages.error(request, "You are not authorized to view this analytics.")
        return redirect('classroom_detail', classroom_id=classroom.id)

    enrolled_students = classroom.enrollment_set.all().values_list('student__username', flat=True)
    submissions = QuizSubmission.objects.filter(quiz=quiz, is_submitted=True)
    attempted_students = submissions.values_list('student__username', flat=True)
    absent_students = list(set(enrolled_students) - set(attempted_students))
    scores = [sub.total_score for sub in submissions]

    highest_score = max(scores) if scores else 0
    lowest_score = min(scores) if scores else 0
    average_score = round(sum(scores) / len(enrolled_students), 2) if enrolled_students else 0.0

    highest_scorers = submissions.filter(total_score=highest_score).values_list('student__username', flat=True)
    lowest_scorers = submissions.filter(total_score=lowest_score).values_list('student__username', flat=True)

    distribution_labels = []
    distribution_data = []
    if scores:
        bins = [0, 50, 70, 85, 100]
        labels = ['0-49%', '50-69%', '70-84%', '85-100%']
        bin_counts = [0] * (len(bins) - 1)

        for score in scores:
            for i in range(len(bins) - 1):
                if bins[i] <= score < bins[i + 1] or (i == len(bins) - 2 and score == 100):
                    bin_counts[i] += 1
                    break

        distribution_labels = labels
        distribution_data = bin_counts

    most_attempted_questions = []
    least_attempted_questions = []
    most_incorrect_questions = []

    question_attempts = Answer.objects.filter(submission__quiz=quiz).values('question').annotate(attempts=Count('id'))
    if question_attempts:
        max_attempt = max([q['attempts'] for q in question_attempts])
        min_attempt = min([q['attempts'] for q in question_attempts])

        for qa in question_attempts:
            try:
                question = Question.objects.get(id=qa['question'])
                if qa['attempts'] == max_attempt:
                    most_attempted_questions.append(question.question_text)
                if qa['attempts'] == min_attempt:
                    least_attempted_questions.append(question.question_text)
            except Question.DoesNotExist:
                continue  # Skip if question missing

    incorrect_answers = Answer.objects.filter(submission__quiz=quiz, is_correct=False).values('question').annotate(wrong_count=Count('id'))
    if incorrect_answers:
        max_wrong = max([q['wrong_count'] for q in incorrect_answers])

        for qa in incorrect_answers:
            try:
                if qa['wrong_count'] == max_wrong:
                    question = Question.objects.get(id=qa['question'])
                    most_incorrect_questions.append(question.question_text)
            except Question.DoesNotExist:
                continue  # Skip if question missing

    submissions = submissions.select_related('student')
    leaderboard = submissions.order_by('-total_score')

    context = {
        'quiz': quiz,
        'highest_score': round(highest_score, 2),
        'lowest_score': round(lowest_score, 2),
        'average_score': round(average_score, 2),
        'highest_scorers': highest_scorers,
        'lowest_scorers': lowest_scorers,
        'absent_students': absent_students,
        'attempted_students': list(attempted_students),
        'distribution_labels': distribution_labels,
        'distribution_data': distribution_data,
        'most_attempted_questions': most_attempted_questions,
        'least_attempted_questions': least_attempted_questions,
        'most_incorrect_questions': most_incorrect_questions,
        'leaderboard': leaderboard,
    }

    return render(request, 'classroom/quiz_analytics.html', context)

#-------------------------------------------------------------


@login_required
def download_quiz_analytics_pdf(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    if request.user != quiz.classroom.created_by:
        messages.error(request, "You are not authorized to download analytics.")
        return redirect('view_quiz', quiz_id=quiz.id)

    submissions = quiz.submissions.filter(is_submitted=True)
    highest_score = submissions.aggregate(Max('total_score'))['total_score__max'] or 0
    lowest_score = submissions.aggregate(Min('total_score'))['total_score__min'] or 0
    average_score = round(submissions.aggregate(Avg('total_score'))['total_score__avg'] or 0, 2)

    leaderboard = submissions.order_by('-total_score', 'submitted_at')

    all_students = Enrollment.objects.filter(classroom=quiz.classroom).values_list('student__username', flat=True)
    attempted_students = submissions.values_list('student__username', flat=True)
    absent_students = list(set(all_students) - set(attempted_students))

    template_path = 'classroom/quiz_analytics_pdf.html'

    context = {
        'quiz': quiz,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'average_score': average_score,
        'leaderboard': leaderboard,
        'absent_students': absent_students,
        'attempted_students': attempted_students,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quiz_{quiz_id}_analytics.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        messages.error(request, "An error occurred while generating the PDF.")
        return redirect('quiz_analytics', quiz_id=quiz.id)

    return response

#-------------------------------------------------------------

@login_required
def share_quiz_results_as_announcement(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.user != quiz.classroom.created_by:
        messages.error(request, "You are not authorized to share quiz results.")
        return redirect('view_quiz', quiz_id=quiz.id)
    
    if request.method == 'POST':
        # Generate CSV in memory
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(['Student Name', 'Email', 'Marks'])
        
        enrolled_students = Enrollment.objects.filter(classroom=quiz.classroom).select_related('student')
        
        for enrollment in enrolled_students:
            student = enrollment.student
            submission = quiz.submissions.filter(student=student, is_submitted=True).first()
            score = submission.get_score() if submission else 0
            writer.writerow([
                student.get_full_name() or student.username,
                student.email,
                score
            ])
        
        # Create announcement with the CSV file
        csv_file = ContentFile(csv_buffer.getvalue().encode())
        file_name = f"{quiz.title}_results.csv"
        
        announcement = Announcement(
            title=f"Quiz Results: {quiz.title}",
            content=f"The results for the quiz '{quiz.title}' are now available. Please find the attached CSV file with all student results.",
            classroom=quiz.classroom,
            created_by=request.user
        )
        announcement.save()
        
        # Attach the CSV file
        announcement.file.save(file_name, csv_file)
        
        messages.success(request, "Quiz results shared as announcement successfully!")
        return redirect('classroom_detail', classroom_id=quiz.classroom.id)
    
    return redirect('view_quiz', quiz_id=quiz.id)

#-------------------------------------------------------------

@login_required
def discussion_forum(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    is_creator = request.user == classroom.created_by
    is_enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()
    
    if not (is_creator or is_enrolled):
        messages.error(request, "You don't have permission to access this forum")
        return redirect('classroom_detail', classroom_id=classroom.id)
    
    if request.method == 'POST':
        form = DiscussionThreadForm(request.POST)
        if form.is_valid():
            try:
                thread = form.save(commit=False)
                thread.classroom = classroom
                thread.created_by = request.user
                
                if DiscussionThread.objects.filter(classroom=classroom, title__iexact=thread.title).exists():
                    messages.warning(request, "A thread with this title already exists")
                    return redirect('discussion_forum', classroom_id=classroom.id)
                
                thread.save()
                messages.success(request, "Thread created successfully!")
                return redirect('discussion_thread', thread_id=thread.id)
            except IntegrityError:
                messages.error(request, "Error creating thread. Please try again.")
    else:
        form = DiscussionThreadForm()
    
    threads = DiscussionThread.objects.filter(classroom=classroom).select_related('created_by')
    
    context = {
        'classroom': classroom,
        'threads': threads,
        'form': form,
        'is_creator': is_creator,
    }
    return render(request, 'classroom/discussion_forum.html', context)

#-------------------------------------------------------------

@login_required
def discussion_thread(request, thread_id):
    thread = get_object_or_404(
        DiscussionThread.objects.select_related('classroom', 'created_by'),
        id=thread_id
    )
    classroom = thread.classroom
    is_creator = request.user == classroom.created_by
    is_enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()
    
    if not (is_creator or is_enrolled):
        messages.error(request, "You don't have permission to view this thread")
        return redirect('classroom:classroom_detail', classroom_id=classroom.id)
    
    if request.method == 'POST':
        form = DiscussionMessageForm(request.POST)
        if form.is_valid():
            try:
                recent_posts = DiscussionMessage.objects.filter(
                    created_by=request.user,
                    created_at__gte=timezone.now()-timezone.timedelta(minutes=1)
                ).count()
                
                if recent_posts >= 3:
                    messages.warning(request, "You're posting too quickly. Please wait a moment.")
                    return redirect('discussion_thread', thread_id=thread.id)
                
                message = form.save(commit=False)
                message.thread = thread
                message.created_by = request.user
                message.save()
                
                thread.last_activity = timezone.now()
                thread.save()
                
                return redirect(f"{reverse('discussion_thread', args=[thread.id])}#message-{message.id}")
            except IntegrityError:
                messages.error(request, "Error posting message. Please try again.")
    else:
        form = DiscussionMessageForm()
    
    thread_messages = thread.messages.select_related(
        'created_by', 'parent_message', 'parent_message__created_by'
    ).prefetch_related(
        'reactions', 'reactions__user'
    ).order_by('created_at')
    
    context = {
        'thread': thread,
        'classroom': classroom,
        'thread_messages': thread_messages,
        'form': form,
        'is_creator': is_creator,
    }
    return render(request, 'classroom/discussion_thread.html', context)

#-------------------------------------------------------------

@login_required
def add_message_reaction(request, message_id, reaction):
    message = get_object_or_404(DiscussionMessage, id=message_id)
    classroom = message.thread.classroom
    
    if not Enrollment.objects.filter(classroom=classroom, student=request.user).exists():
        messages.error(request, "You don't have permission to react")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('discussion_thread', args=[message.thread.id])))
    
    # Convert emoji to reaction key if needed
    reaction_key = MessageReaction.REVERSE_REACTION_MAP.get(reaction, reaction)
    
    if reaction_key not in dict(MessageReaction.REACTION_CHOICES):
        messages.error(request, "Invalid reaction")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('discussion_thread', args=[message.thread.id])))
    
    try:
        existing = MessageReaction.objects.get(message=message, user=request.user)
        if existing.reaction == reaction_key:
            existing.delete()
            # Don't show message for removing reactions
        else:
            existing.reaction = reaction_key
            existing.save()
            # Don't show message for updating reactions
    except MessageReaction.DoesNotExist:
        MessageReaction.objects.create(
            message=message,
            user=request.user,
            reaction=reaction_key
        )
        # Don't show message for adding reactions
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('discussion_thread', args=[message.thread.id])))

#-------------------------------------------------------------

@login_required
def reply_to_message(request, message_id):
    parent_message = get_object_or_404(DiscussionMessage, id=message_id)
    classroom = parent_message.thread.classroom
    is_creator = request.user == classroom.created_by
    is_enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()
    
    if not (is_creator or is_enrolled):
        messages.error(request, "You don't have permission to reply")
        return redirect('classroom_detail', classroom_id=classroom.id)
    
    if request.method == 'POST':
        form = DiscussionMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.thread = parent_message.thread
            message.created_by = request.user
            message.parent_message = parent_message
            message.save()
            
            # Update thread activity
            parent_message.thread.last_activity = timezone.now()
            parent_message.thread.save()
            
            return redirect(f"{reverse('discussion_thread', args=[parent_message.thread.id])}#message-{message.id}")
    
    return redirect('discussion_thread', thread_id=parent_message.thread.id)

#-------------------------------------------------------------

@login_required
def toggle_pin_thread(request, thread_id):
    thread = get_object_or_404(DiscussionThread, id=thread_id)
    
    if request.user != thread.classroom.created_by:
        messages.error(request, "Only teachers can pin threads")
        return redirect('discussion_thread', thread_id=thread.id)
    
    thread.is_pinned = not thread.is_pinned
    thread.save()
    
    return redirect('discussion_forum', classroom_id=thread.classroom.id)

#-------------------------------------------------------------

@login_required
def delete_thread(request, thread_id):
    thread = get_object_or_404(DiscussionThread.objects.select_related('classroom', 'created_by'), id=thread_id)
    classroom = thread.classroom
    
    # Check permissions
    if not (request.user == thread.created_by or request.user == classroom.created_by):
        messages.error(request, "You don't have permission to delete this thread")
        return redirect('discussion_forum', classroom_id=classroom.id)
    
    if request.method == 'POST':
        # Perform deletion
        classroom_id = thread.classroom.id
        thread_title = thread.title
        thread.delete()
        messages.success(request, f"Thread '{thread_title}' deleted successfully")
        return redirect('discussion_forum', classroom_id=classroom_id)
    
    # If GET request, show confirmation template
    context = {
        'thread': thread,
        'classroom': classroom,
    }
    return render(request, 'classroom/confirm_thread_delete.html', context)

#-------------------------------------------------------------

@login_required
@csrf_exempt
def verify_current_credentials(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            user = authenticate(request, username=request.user.username, password=password)
            
            if user is not None and user.email == email:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

#-------------------------------------------------------------

@login_required
@csrf_exempt
def send_verification_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_username = data.get('new_username')
            new_email = data.get('new_email')
            new_password = data.get('new_password')
            
            # Validate new username
            if not re.match(r'^[a-zA-Z0-9_]{4,}$', new_username):
                return JsonResponse({'success': False, 'error': 'Invalid username format'}, status=400)
                
            # Validate new email
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', new_email):
                return JsonResponse({'success': False, 'error': 'Invalid email format'}, status=400)
                
            # Validate password strength
            if (len(new_password) < 8 or 
                not any(c.isupper() for c in new_password) or 
                not any(c.islower() for c in new_password) or 
                not any(c.isdigit() for c in new_password) or 
                not any(c in "!@#$%^&*()-_=+" for c in new_password)):
                return JsonResponse({'success': False, 'error': 'Password does not meet requirements'}, status=400)
            
            # Check if username or email already exists (excluding current user)
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                return JsonResponse({'success': False, 'error': 'Username already taken'}, status=400)
                
            if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                return JsonResponse({'success': False, 'error': 'Email already in use'}, status=400)
            
            # Generate and save verification code
            code = str(random.randint(100000, 999999))
            EmailVerificationCode.objects.update_or_create(
                email=new_email,
                defaults={'code': code, 'created_at': timezone.now()}
            )
            
            # Send verification email
            subject = 'ClassConnect: Verify Your Email Change'
            message = f'''
            Hi {request.user.username},
            
            You've requested to change your ClassConnect account credentials. 
            Please use the following verification code to confirm this change:
            
            Verification Code: {code}
            
            This code will expire in 10 minutes.
            
            If you didn't request this change, please contact support immediately.
            
            — ClassConnect Team
            '''
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [new_email]
            
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            
            # Store new credentials in session temporarily
            request.session['new_credentials'] = {
                'username': new_username,
                'email': new_email,
                'password': new_password
            }
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

#-------------------------------------------------------------

@login_required
@csrf_exempt
def verify_update_credentials(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            input_code = data.get('code')
            
            if 'new_credentials' not in request.session:
                return JsonResponse({'success': False, 'error': 'Session expired'}, status=400)
                
            new_credentials = request.session['new_credentials']
            new_email = new_credentials['email']
            
            try:
                verification = EmailVerificationCode.objects.get(email=new_email)
            except EmailVerificationCode.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Verification not found'}, status=400)
                
            if verification.is_expired():
                return JsonResponse({'success': False, 'error': 'Verification code expired'}, status=400)
                
            if str(verification.code) != input_code:
                return JsonResponse({'success': False, 'error': 'Invalid verification code'}, status=400)
            
            # Update user credentials
            user = request.user
            user.username = new_credentials['username']
            user.email = new_credentials['email']
            user.set_password(new_credentials['password'])
            user.save()
            
            # Clean up
            verification.delete()
            del request.session['new_credentials']
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

#-------------------------------------------------------------

@login_required
@csrf_exempt
def resend_verification_code(request):
    if request.method == 'POST':
        try:
            if 'new_credentials' not in request.session:
                return JsonResponse({'success': False, 'error': 'Session expired'}, status=400)
                
            new_credentials = request.session['new_credentials']
            new_email = new_credentials['email']
            
            # Generate new code
            code = str(random.randint(100000, 999999))
            EmailVerificationCode.objects.update_or_create(
                email=new_email,
                defaults={'code': code, 'created_at': timezone.now()}
            )
            
            # Send verification email
            subject = 'ClassConnect: New Verification Code'
            message = f'''
            Hi {request.user.username},
            
            Here's your new verification code for changing your ClassConnect account credentials:
            
            Verification Code: {code}
            
            This code will expire in 10 minutes.
            
            — ClassConnect Team
            '''
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [new_email]
            
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)