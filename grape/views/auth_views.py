"""
Authentication views - login, logout, create account, edit account
"""
import re
import hashlib
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

from grape.models import Person, Profile, EmailConfirmation
from grape.helpers import generate_pid, generate_post_id
from grape.hashers import make_grape_password, check_grape_password


def _make_password(raw_password):
    return make_grape_password(raw_password)


def _check_password(raw_password, hashed):
    return check_grape_password(raw_password, hashed)


def _validate_user_id(user_id):
    return bool(re.match(r'^[A-Za-z0-9\-._]{6,20}$', user_id))


def login_view(request):
    """Login page - redirects to offdevice login or portal login based on context"""
    is_offdevice = request.path.startswith('/web/')
    tpl = 'offdevice/login.html' if is_offdevice else 'portal/login.html'

    if request.session.get('pid'):
        return redirect('/')

    error = None
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        password = request.POST.get('password', '')

        if not user_id:
            error = 'You did not enter a login ID.'
        elif not password:
            error = 'The password field cannot be blank.'
        else:
            try:
                user = Person.objects.get(user_id=user_id)
                if user.ban_status >= 4:
                    error = 'This account has been banned.'
                elif not _check_password(password, user.password):
                    error = 'The login ID or password you entered is incorrect.'
                else:
                    request.session['signed_in'] = True
                    request.session['pid'] = user.pid
                    request.session['user_id'] = user.user_id
                    location = request.GET.get('location', '/')
                    return redirect(location)
            except Person.DoesNotExist:
                error = 'The login ID or password you entered is incorrect.'

    return render(request, tpl, {'error': error, 'location': request.GET.get('location', '/')})


def logout_view(request):
    request.session.flush()
    location = request.GET.get('location', '/')
    return redirect(location)


def create_account_view(request):
    """Account creation"""
    is_offdevice = request.path.startswith('/web/')
    tpl = 'offdevice/create_account.html' if is_offdevice else 'portal/create_account.html'

    if not getattr(settings, 'GRAPE_ALLOW_SIGNUP', True):
        return HttpResponse('Signups are currently disabled.', status=403)

    errors = []
    form_data = {}

    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        screen_name = request.POST.get('screen_name', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        email = request.POST.get('email', '').strip()

        form_data = {
            'user_id': user_id,
            'screen_name': screen_name,
            'email': email,
        }

        if not user_id:
            errors.append('You did not enter a login ID.')
        elif not _validate_user_id(user_id):
            errors.append('Your login ID is too short, too long, or contains characters that cannot be used.')
        elif Person.objects.filter(user_id=user_id).exists():
            errors.append('The login ID you have entered already exists.')

        if not screen_name or not screen_name.strip():
            errors.append('You did not enter a screen name.')
        elif len(screen_name) > 17:
            errors.append('Your screen name is too long.')

        if not password:
            errors.append('The password field cannot be blank.')
        elif password != password2:
            errors.append('The passwords you have entered do not match.')

        if not errors:
            pid = generate_pid()
            hashed_pw = _make_password(password)
            user = Person.objects.create(
                pid=pid,
                user_id=user_id,
                screen_name=screen_name,
                password=hashed_pw,
                email=email if email else None,
                platform_id=1,
            )
            Profile.objects.create(pid=pid, platform_id=1)
            request.session['signed_in'] = True
            request.session['pid'] = pid
            request.session['user_id'] = user_id
            return redirect('/')

    return render(request, tpl, {'errors': errors, 'form_data': form_data})


def edit_account_view(request):
    """Edit account (screen name, password)"""
    if not request.session.get('pid'):
        return redirect('/act/login')

    is_offdevice = request.path.startswith('/web/')
    tpl = 'offdevice/edit_account.html' if is_offdevice else 'portal/edit_account.html'

    pid = request.session['pid']
    try:
        user = Person.objects.get(pid=pid)
    except Person.DoesNotExist:
        request.session.flush()
        return redirect('/act/login')

    errors = []
    if request.method == 'POST':
        screen_name = request.POST.get('screen_name', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not screen_name:
            errors.append('You did not enter a screen name.')
        elif len(screen_name) > 17:
            errors.append('Your screen name is too long.')
        elif password and password != password2:
            errors.append('The passwords you have entered do not match.')

        if not errors:
            user.screen_name = screen_name
            if password:
                user.password = _make_password(password)
            user.save()
            return redirect('/my_menu')

    return render(request, tpl, {'user': user, 'errors': errors})
