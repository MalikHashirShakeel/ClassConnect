from django.views.generic import TemplateView
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('accept-terms/', views.accept_terms, name='accept_terms'),  
    path('welcome/', views.welcome_page, name='welcome_page'),
    path('login/', views.login_view, name='login'),
    path('welcome-back/', views.welcome_back, name='welcome_back'),
    path('logout/', views.user_logout, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code_view, name='verify_reset_code'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path("resources/help-center/", TemplateView.as_view(template_name="resources/help_center.html"), name="help_center"),
    path("resources/privacy-policy/", TemplateView.as_view(template_name="resources/privacy_policy.html"), name="privacy_policy"),
    path("resources/terms-of-service/", TemplateView.as_view(template_name="resources/terms_of_service.html"), name="terms_of_service"),
    path("resources/documentation/", TemplateView.as_view(template_name="resources/documentation.html"), name="documentation"),
]