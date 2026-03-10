"""
Management command to create a Grape user account.
Use this instead of createsuperuser — that creates Django admin users,
not Grape users. Grape users live in the 'people' table.

Usage:
    python manage.py grape_createuser
    python manage.py grape_createuser --admin   (sets privilege=10 + status=3)
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Create a Grape user account (in the people table, not Django auth)'

    def add_arguments(self, parser):
        parser.add_argument('--admin', action='store_true', help='Give admin privileges (privilege=10, status=3)')
        parser.add_argument('--user_id', type=str, help='Login ID (skip prompt)')
        parser.add_argument('--screen_name', type=str, help='Screen name (skip prompt)')
        parser.add_argument('--password', type=str, help='Password (skip prompt)')

    def handle(self, *args, **options):
        from grape.models import Person, Profile
        from grape.helpers import generate_pid
        from grape.hashers import make_grape_password
        import re

        self.stdout.write(self.style.WARNING(
            '\nThis creates a Grape user (people table), not a Django admin user.\n'
            'To access /admin/, use: python manage.py createsuperuser\n'
        ))

        # user_id
        user_id = options.get('user_id')
        while not user_id:
            user_id = input('Login ID (6-20 chars, letters/numbers/-._): ').strip()
            if not re.match(r'^[A-Za-z0-9\-._]{6,20}$', user_id):
                self.stdout.write(self.style.ERROR('Invalid login ID.'))
                user_id = None
            elif Person.objects.filter(user_id=user_id).exists():
                self.stdout.write(self.style.ERROR('Login ID already exists.'))
                user_id = None

        # screen_name
        screen_name = options.get('screen_name')
        while not screen_name:
            screen_name = input('Screen name (max 17 chars): ').strip()
            if not screen_name or len(screen_name) > 17:
                self.stdout.write(self.style.ERROR('Invalid screen name.'))
                screen_name = None

        # password
        import getpass
        password = options.get('password')
        while not password:
            password = getpass.getpass('Password: ')
            password2 = getpass.getpass('Confirm password: ')
            if password != password2:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                password = None
            elif len(password) < 6:
                self.stdout.write(self.style.ERROR('Password too short (min 6 chars).'))
                password = None

        is_admin = options.get('admin', False)

        pid = generate_pid()
        hashed_pw = make_grape_password(password)

        try:
            user = Person.objects.create(
                pid=pid,
                user_id=user_id,
                screen_name=screen_name,
                password=hashed_pw,
                platform_id=1,
                privilege=10 if is_admin else 0,
                status=3 if is_admin else 0,
            )
            Profile.objects.get_or_create(pid=pid)
            self.stdout.write(self.style.SUCCESS(
                f'\nGrape user created successfully!\n'
                f'  Login ID:    {user_id}\n'
                f'  Screen name: {screen_name}\n'
                f'  PID:         {pid}\n'
                f'  Admin:       {is_admin}\n'
            ))
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating user: {e}'))
