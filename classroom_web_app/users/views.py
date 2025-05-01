from django.shortcuts import render, redirect
from .forms import ForgotPasswordForm, VerifyCodeForm, SetNewPasswordForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import re
from captcha.fields import CaptchaField
from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerificationCode
from django.core.mail import send_mail
from django.conf import settings
import random
from email.utils import formataddr
from django.core.mail import EmailMultiAlternatives
import logging
from django.core.cache import cache


logger = logging.getLogger(__name__)

class CaptchaTestForm(forms.Form):
    captcha = CaptchaField()

#------------------------------------------------------------

def is_strong_password(password):
    """Check if the password meets security requirements."""
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(c in "!@#$%^&*()-_=+" for c in password)
    )

#------------------------------------------------------------

def send_verification_email(email, username, code):
    subject = 'ClassConnect: Your Login OTP'  # Less spammy subject
    from_email = formataddr(('ClassConnect', settings.DEFAULT_FROM_EMAIL))
    
    # Add List-Unsubscribe header
    headers = {
        'List-Unsubscribe': '<https://yourdomain.com/unsubscribe>',
        'X-Mailer': 'ClassConnect Mailer',
    }

    text_content = f"""
Hi {username},

Welcome to ClassConnect! Here's your login Code:

Verification Code: {code}

This Code expires in 10 minutes.

If you didn't request this, please ignore this email.

Need help? Contact support@classconnect.com

Unsubscribe: https://yourdomain.com/unsubscribe

— ClassConnect Team
"""

    html_content = f"""
<div style="font-family:Arial,sans-serif;background-color:#f9f9ff;padding:20px;">
    <h2 style="color:#7c3aed;">Hi {username},</h2>
    <p>Welcome to <strong>ClassConnect</strong>! Here's your login Code:</p>
    <div style="font-size:24px; font-weight:bold; color:#10b981; padding:10px 0;">{code}</div>
    <p>This Code expires in <strong>10 minutes</strong>.</p>
    <p style="color:#888;">If you didn't request this email, please ignore it.</p>
    <p><a href="mailto:support@classconnect.com">Contact support</a></p>
    <p style="font-size:12px;color:#999;">
        <a href="https://yourdomain.com/unsubscribe" style="color:#999;">Unsubscribe</a>
    </p>
    <br>
    <p style="color:#666;">— The ClassConnect Team</p>
</div>
"""

    msg = EmailMultiAlternatives(
        subject, 
        text_content, 
        from_email, 
        [email],
        headers=headers
    )
    msg.attach_alternative(html_content, "text/html")
    
    # Set important headers
    msg.extra_headers = {
        'Precedence': 'bulk',  # For transactional emails
        'X-Priority': '1',  # High priority
    }
    
    try:
        msg.send()
    except Exception as e:
        # Log email sending errors
        logger.error(f"Failed to send verification email to {email}: {str(e)}")

#------------------------------------------------------------

def generate_verification_code():
    """Return a random 6-digit code as string."""
    return str(random.randint(100000, 999999))

#------------------------------------------------

def register(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        captcha_form = CaptchaTestForm(request.POST)

        if not captcha_form.is_valid():
            messages.error(request, "Invalid CAPTCHA. Please try again.")
        elif not re.match(r'^[a-zA-Z0-9_]{4,}$', username):
            messages.error(request, "Username must be at least 4 characters and contain only letters, numbers, and underscores.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Enter a valid email address.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif not is_strong_password(password1):
            messages.error(request, "Password must be strong with all required characters.")
        else:
            # Save valid form data temporarily in session
            request.session['registration_data'] = {
                'username': username,
                'email': email,
                'password': password1,
            }

            # Generate 6-digit code
            code = generate_verification_code()

            # Create or update verification code
            EmailVerificationCode.objects.update_or_create(
                email=email,
                defaults={'code': code, 'created_at': timezone.now()}
            )

            # Send improved verification email
            send_verification_email(email, username, code)

            return redirect('verify_code')

    else:
        captcha_form = CaptchaTestForm()

    return render(request, 'register.html', {'captcha_form': captcha_form})

#------------------------------------------------------------

def verify_code(request):
    if request.method == 'POST':
        input_code = request.POST.get('code').strip()
        reg_data = request.session.get('registration_data')

        if not reg_data:
            messages.error(request, "Session expired. Please start over.")
            return redirect('register')

        try:
            verification = EmailVerificationCode.objects.get(email=reg_data['email'])
        except EmailVerificationCode.DoesNotExist:
            messages.error(request, "Verification entry not found.")
            return redirect('register')

        if str(verification.code) != input_code:
            messages.error(request, "Invalid verification code.")
        elif verification.is_expired():
            messages.error(request, "Verification code has expired. Please restart.")
            return redirect('register')
        else:
            # Mark as verified in session
            request.session['verified_email'] = True
            return redirect('accept_terms')

    return render(request, 'verify_code.html')

#-------------------------------------------------


def accept_terms(request):
    reg_data = request.session.get('registration_data')
    verified = request.session.get('verified_email')

    if not reg_data or not verified:
        messages.error(request, "Session expired or invalid access.")
        return redirect('register')

    if request.method == 'POST':
        if not request.POST.get('accept_terms') or not request.POST.get('accept_privacy'):
            messages.error(request, "You must accept both the Terms of Service and the Privacy Policy.")
        else:
            user = User.objects.create(
                username=reg_data['username'],
                email=reg_data['email'],
                password=make_password(reg_data['password'])
            )
            login(request, user)
            # Clean up
            request.session.pop('registration_data', None)
            request.session.pop('verified_email', None)
            messages.success(request, "Account created successfully.")
            return redirect('welcome_page')

    return render(request, 'accept_terms.html')

#-------------------------------------------------

@login_required
def welcome_page(request):
    return render(request, 'welcome.html')

#-------------------------------------------------

@login_required
def welcome_back(request):
    return render(request, 'welcome_back.html')

#-------------------------------------------------

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password']
        captcha_form = CaptchaTestForm(request.POST)

        # CAPTCHA Validation
        if not captcha_form.is_valid():
            messages.error(request, "Invalid CAPTCHA. Please try again.")
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")

                # Check if user is a superuser
                if user.is_superuser:
                    return redirect('/admin/')  # Redirect to Django admin panel

                return redirect('welcome_back')
            else:
                messages.error(request, "Invalid username or password.")

    else:
        captcha_form = CaptchaTestForm()

    return render(request, 'login.html', {'captcha_form': captcha_form})

#------------------------------------------------------------

def user_logout(request):
    """Log out the user and redirect to the homepage."""
    logout(request)
    return redirect('/')  

#------------------------------------------------------------

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Shouldn't happen due to form validation, but we double guard anyway!
                messages.error(request, "No account found with that email.")
                return redirect('forgot_password')

            # Rate limit
            rate_key = f"reset_attempts_{email}"
            attempts = cache.get(rate_key, 0)
            if attempts >= 5:
                messages.error(request, "You've reached the limit. Try again after 10 minutes.")
                return redirect('forgot_password')

            cache.set(rate_key, attempts + 1, timeout=600)

            code = generate_verification_code()
            EmailVerificationCode.objects.update_or_create(
                email=email,
                defaults={'code': code, 'created_at': timezone.now()}
            )

            send_verification_email(email, user.username, code)
            request.session['reset_email'] = email
            messages.success(request, f"A verification code was sent to {email}. Check your inbox.")
            return redirect('verify_reset_code')

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ForgotPasswordForm()

    return render(request, 'auth/forgot_password.html', {'form': form})

#------------------------------------------------------------

def verify_reset_code_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code_input = form.cleaned_data['code']
            try:
                record = EmailVerificationCode.objects.get(email=email)
                if record.code != code_input:
                    messages.error(request, "Incorrect code.")
                elif timezone.now() - record.created_at > timedelta(minutes=10):
                    messages.error(request, "Verification code expired.")
                else:
                    request.session['code_verified'] = True
                    return redirect('reset_password')
            except EmailVerificationCode.DoesNotExist:
                messages.error(request, "Verification record not found.")
    else:
        form = VerifyCodeForm()

    return render(request, 'auth/verify_reset_code.html', {'form': form})

#------------------------------------------------------------

def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email or not request.session.get('code_verified'):
        return redirect('forgot_password')

    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            p1 = form.cleaned_data['password1']
            p2 = form.cleaned_data['password2']
            if p1 != p2:
                messages.error(request, "Passwords do not match.")
            elif not is_strong_password(p1):
                messages.error(request, "Password must be strong with all required characters.")
            else:
                try:
                    user = User.objects.get(email=email)
                    user.set_password(p1)
                    user.save()
                    messages.success(request, "Password successfully reset.")
                    # Clean session
                    for key in ['reset_email', 'code_verified']:
                        if key in request.session:
                            del request.session[key]
                    return redirect('login')
                except User.DoesNotExist:
                    messages.error(request, "User not found.")
    else:
        form = SetNewPasswordForm()

    return render(request, 'auth/reset_password.html', {'form': form})