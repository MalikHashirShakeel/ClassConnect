from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Classroom, Enrollment, Announcement, Assignment, Submission, Comment, Invitation, Choice, Quiz, QuizSubmission, Answer
from .forms import ClassroomForm, AnnouncementForm, AssignmentForm, QuestionForm, QuizInfoForm
from django.forms import formset_factory
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime
from django.utils.timezone import is_naive, make_aware
import csv
from django.http import HttpResponse

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
            return redirect('classroom_list')
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
        class_code = request.POST.get('class_code')
        try:
            classroom = Classroom.objects.get(class_code=class_code)
            # Check if the user is already enrolled
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

@login_required
def classroom_detail(request, classroom_id):
    """View to display classroom details and pending/missed tasks for students."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    is_creator = classroom.created_by == request.user

    # Get all announcements and assignments for the classroom
    announcements = Announcement.objects.filter(classroom=classroom).order_by('-created_at')
    assignments = Assignment.objects.filter(classroom=classroom).order_by('-created_at')
    quizzes = Quiz.objects.filter(classroom=classroom).order_by('-start_time')

    # For students, calculate pending and missed tasks
    pending_tasks = []
    missed_tasks = []
    if not is_creator:
        now = timezone.now()
        for assignment in assignments:
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

        for quiz in quizzes:
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
        'quizzes': quizzes,  # Added quizzes to the context
    }
    return render(request, 'classroom/classroom_detail.html', context)


#------------------------------------------------------------

@login_required
def add_announcement(request, classroom_id):
    """View to add an announcement to a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.classroom = classroom
            announcement.created_by = request.user
            announcement.save()
            return redirect('classroom_detail', classroom_id=classroom.id)
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
    return redirect('classroom_detail', classroom_id=announcement.classroom.id)

#-------------------------------------------------------------

@login_required
def add_assignment(request, classroom_id):
    """View to add an assignment to a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.classroom = classroom
            assignment.created_by = request.user
            assignment.save()
            return redirect('classroom_detail', classroom_id=classroom.id)
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
        assignment.delete()
    return redirect('classroom_detail', classroom_id=assignment.classroom.id)

#------------------------------------------------------------

@login_required
def view_announcement(request, announcement_id):
    """View to display the full details of an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    is_creator = announcement.created_by == request.user

    context = {
        'announcement': announcement,
        'is_creator': is_creator,
    }
    return render(request, 'classroom/view_announcement.html', context)

#------------------------------------------------------------

@login_required
def edit_announcement(request, announcement_id):
    """View to edit an announcement."""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if announcement.created_by != request.user:
        return redirect('view_announcement', announcement_id=announcement.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect('view_announcement', announcement_id=announcement.id)
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
    is_creator = assignment.created_by == request.user
    is_due_date_passed = timezone.now() > assignment.due_date
    submission = Submission.objects.filter(assignment=assignment, student=request.user).first()

    context = {
        'assignment': assignment,
        'is_creator': is_creator,
        'is_due_date_passed': is_due_date_passed,
        'submission': submission,
    }
    return render(request, 'classroom/view_assignment.html', context)

#------------------------------------------------------------

@login_required
def edit_assignment(request, assignment_id):
    """View to edit an assignment."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if assignment.created_by != request.user:
        return redirect('view_assignment', assignment_id=assignment.id)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            return redirect('view_assignment', assignment_id=assignment.id)
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
            return redirect('view_assignment', assignment_id=assignment.id)
    return render(request, 'classroom/submit_assignment.html', {'assignment': assignment})

#------------------------------------------------------------

@login_required
def create_quiz_info(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if classroom.created_by != request.user:
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = QuizInfoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Convert datetime to ISO string before storing in session
            data['start_time'] = data['start_time'].isoformat()
            request.session['quiz_info'] = data
            return redirect('create_quiz_questions', classroom_id=classroom_id)
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
        return redirect('classroom_detail', classroom_id=classroom.id)

    quiz_info = request.session.get('quiz_info')
    if not quiz_info:
        return redirect('create_quiz_info', classroom_id=classroom_id)

    # Convert string back to datetime
    quiz_info['start_time'] = datetime.fromisoformat(quiz_info['start_time'])

    # Make datetime timezone-aware if needed
    start_time = quiz_info['start_time']
    if is_naive(start_time):
        start_time = make_aware(start_time)

    num_questions = int(quiz_info.get('number_of_questions', 1))
    QuestionFormSet = formset_factory(QuestionForm, extra=num_questions)

    if request.method == 'POST':
        formset = QuestionFormSet(request.POST)
        if formset.is_valid():
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
                question.question_type = 'MCQ'  # hardcoded since it's MCQ-only
                question.save()

                # Create 4 choices
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
            return redirect('classroom_detail', classroom_id=classroom_id)
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
    is_creator = quiz.created_by == request.user
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

        for question in quiz.questions.all():
            choice_id = request.POST.get(f"question_{question.id}")
            selected_choice = Choice.objects.filter(id=choice_id, question=question).first()

            is_correct = selected_choice.is_correct if selected_choice else False
            if is_correct:
                total_score += question.points

            Answer.objects.create(
                submission=submission,
                question=question,
                choice=selected_choice,
                is_correct=is_correct
            )
            total_points += question.points

        # Calculate percentage
        submission.total_score = (total_score / total_points) * 100 if total_points else 0
        submission.is_submitted = True
        submission.save()

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
        return redirect('view_quiz', quiz.id)

    if request.method == 'POST':
        classroom_id = quiz.classroom.id
        quiz.delete()
        return redirect('classroom_detail', classroom_id=classroom_id)

    return redirect('view_quiz', quiz.id)

#------------------------------------------------------------

@login_required
def edit_submission(request, submission_id):
    """View to edit a submission."""
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.student != request.user:
        return redirect('view_assignment', assignment_id=submission.assignment.id)

    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            submission.file = file
            submission.save()
            return redirect('view_assignment', assignment_id=submission.assignment.id)
    return render(request, 'classroom/edit_submission.html', {'submission': submission})

#------------------------------------------------------------

@login_required
def cancel_submission(request, submission_id):
    """View to cancel a submission."""
    submission = get_object_or_404(Submission, id=submission_id)
    if submission.student != request.user:
        return redirect('view_assignment', assignment_id=submission.assignment.id)

    submission.delete()
    return redirect('view_assignment', assignment_id=submission.assignment.id)

#------------------------------------------------------------

@login_required
def view_submissions(request, assignment_id):
    """View to display all submissions for an assignment and list students who haven't submitted."""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if assignment.created_by != request.user:
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
    elif object_type == 'quiz':  # ✅ ADD THIS!
        obj = get_object_or_404(Quiz, id=object_id)
        comments = Comment.objects.filter(quiz=obj, parent_comment__isnull=True)
    else:
        return redirect('classroom_list')  

    if request.method == 'POST':
        content = request.POST.get('content')
        Comment.objects.create(
            content=content,
            announcement=obj if object_type == 'announcement' else None,
            assignment=obj if object_type == 'assignment' else None,
            quiz=obj if object_type == 'quiz' else None,
            created_by=request.user
        )
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
        content = request.POST.get('content')
        
        # Create the reply, inheriting the object association from the parent
        Comment.objects.create(
            content=content,
            announcement=parent_comment.announcement,
            assignment=parent_comment.assignment,
            quiz=parent_comment.quiz,  
            created_by=request.user,
            parent_comment=parent_comment
        )

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
        return redirect('classroom_detail', classroom_id=classroom.id)

    # Get all students enrolled in the classroom
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
        return redirect('classroom_detail', classroom_id=classroom.id)

    student = get_object_or_404(User, id=student_id)

    # Delete all related data for the student in this classroom
    Enrollment.objects.filter(classroom=classroom, student=student).delete()  # Remove enrollment
    Comment.objects.filter(created_by=student, announcement__classroom=classroom).delete()  # Delete comments on announcements
    Comment.objects.filter(created_by=student, assignment__classroom=classroom).delete()  # Delete comments on assignments
    Submission.objects.filter(student=student, assignment__classroom=classroom).delete()  # Delete assignment submissions

    return redirect('view_students', classroom_id=classroom.id)

#-------------------------------------------------------------

@login_required
def add_student(request, classroom_id):
    """View to send an invitation to a student by email."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if classroom.created_by != request.user:
        return redirect('classroom_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            student = User.objects.get(email=email)
            # Check if the student is already enrolled or invited
            if Enrollment.objects.filter(classroom=classroom, student=student).exists():
                messages.warning(request, f'{student.username} is already enrolled in this classroom.')
            elif Invitation.objects.filter(classroom=classroom, student=student, is_accepted=False).exists():
                messages.warning(request, f'{student.username} has already been invited to this classroom.')
            else:
                # Send an invitation
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
        return redirect('classroom_list')  # Redirect if the user is not the creator

    if request.method == 'POST':
        
        classroom.delete()
        return redirect('classroom_list') 

    return redirect('classroom_detail', classroom_id=classroom.id)

#------------------------------------------------------------

@login_required
def leave_classroom(request, classroom_id):
    """View for a student to leave a classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == 'POST':
        # Remove the student from the classroom
        Enrollment.objects.filter(classroom=classroom, student=request.user).delete()
        return redirect('classroom_list')  # Redirect to the classroom list after leaving

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

    # Process Assignments
    for assignment in assignments:
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

    # Process Quizzes
    for quiz in quizzes:
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
        # Enroll the student in the classroom
        Enrollment.objects.create(
            classroom=invitation.classroom,
            student=request.user,
            enrolled_at=timezone.now()
        )
        invitation.is_accepted = True
        invitation.save()
        messages.success(request, f'You have successfully joined {invitation.classroom.name}!')
    else:
        messages.warning(request, 'This invitation has already been accepted.')

    return redirect('classroom_list')

#-------------------------------------------------------------

@login_required
def invitations(request):
    """View to display pending invitations."""
    invitations = Invitation.objects.filter(student=request.user, is_accepted=False)
    context = {
        'invitations': invitations,
    }
    return render(request, 'classroom/invitations.html', context)

#-------------------------------------------------------------

@login_required
def download_quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.user != quiz.classroom.created_by:
        return redirect('view_quiz', quiz_id=quiz.id)

    # Prepare CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{quiz.title}_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Marks'])

    # Get all enrolled students
    enrolled_students = Enrollment.objects.filter(classroom=quiz.classroom).select_related('student')

    for enrollment in enrolled_students:
        student = enrollment.student
        submission = quiz.submissions.filter(student=student, is_submitted=True).first()
        
        if submission:
            try:
                score = submission.get_score()
            except:
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