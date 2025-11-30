from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User

def register_view(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Basic validation
        if password1 != password2:
            messages.error(request, "Passwords don't match!")
            return render(request, 'register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'register.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            login(request, user)
            messages.success(request, f"Welcome {user.username}! Registration successful.")
            return redirect('home')
        except Exception as e:
            messages.error(request, "Error creating account. Please try again.")
            return render(request, 'register.html')
    
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password!")
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')