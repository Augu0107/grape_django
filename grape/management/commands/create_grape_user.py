"""
Management command to create a user in the Grape 'people' table.
This is separate from Django's auth system (which is only used for /admin/).

Usage:
    python manage.py create_grape_user
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import getpass
import re


class Command(BaseCommand):
    help = 'Create a new Grape user in the people table (for site login, not /admin/)'

    def handle(self, *args, **options):
        from grape.models import Person, Profile
        from grape.hashers import make_grape_password
        from grape.helpers import generate_pid

        self.stdout.write(self.style.WARNING(
            '\nThis creates a user for the SITE (people table).\n'
            'For /admin/ access, use: python manage.py createsuperuser\n'
            'These are TWO SEPARATE login systems.\n'
        ))

        # user_id
        while True:
            user_id = input('Login ID (6-20 chars, letters/numbers/-._): ').strip()
            if not re.match(r'^[A-Za-z0-9\-._]{6,20}$', user_id):
                self.stdout.write(self.style.ERROR('Invalid login ID format.'))
                continue
            if Person.objects.filter(user_id=user_id).exists():
                self.stdout.write(self.style.ERROR('That login ID already exists.'))
                continue
            break

        # screen_name
        while True:
            screen_name = input('Screen Name (max 17 chars): ').strip()
            if not screen_name or len(screen_name) > 17:
                self.stdout.write(self.style.ERROR('Screen name must be 1-17 characters.'))
                continue
            break

        # password
        while True:
            password = getpass.getpass('Password: ')
            password2 = getpass.getpass('Confirm Password: ')
            if password != password2:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                continue
            if len(password) < 6:
                self.stdout.write(self.style.ERROR('Password must be at least 6 characters.'))
                continue
            break

        # privilege
        make_admin_str = input('Make this user a site admin (privilege=3)? [y/N]: ').strip().lower()
        privilege = 3 if make_admin_str == 'y' else 0

        pid = generate_pid()
        hashed_pw = make_grape_password(password)

        user = Person.objects.create(
            pid=pid,
            user_id=user_id,
            screen_name=screen_name,
            password=hashed_pw,
            platform_id=1,
            privilege=privilege,
        )
        Profile.objects.get_or_create(pid=pid, defaults={'platform_id': 1})

        self.stdout.write(self.style.SUCCESS(
            f'\nGrape user created successfully!\n'
            f'  Login ID:    {user_id}\n'
            f'  Screen Name: {screen_name}\n'
            f'  PID:         {pid}\n'
            f'  Privilege:   {privilege}\n'
            f'\nThis user can now log in at /web/act/login or /act/login'
        ))
