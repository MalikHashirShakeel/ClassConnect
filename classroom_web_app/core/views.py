from django.shortcuts import render
from django.contrib.auth import logout

# Create your views here.
def landing_page(request):
    if request.user.is_authenticated:
        logout(request)
    return render(request, 'core/landing.html')
