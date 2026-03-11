"""
Grape - Miiverse Clone - Django Settings
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'CHANGE-THIS-IN-PRODUCTION-USE-A-LONG-RANDOM-STRING'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'grape',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'grape.middleware.InterfaceDetectionMiddleware',
]

ROOT_URLCONF = 'grape_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'grape.context_processors.grape_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'grape_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_NAME = 'grp'
SESSION_COOKIE_AGE = 72000

# Grape config
GRAPE_MII_ENDPOINT_PREFIX = 'https://pf2m.com/hash/'
GRAPE_ALLOW_SIGNUP = True
GRAPE_ALLOW_ALLIMAGES = False
GRAPE_ALLOW_BLACKLIST = True
GRAPE_MAX_POSTBUFFERTIME = 2
GRAPE_MAX_REPLYBUFFERTIME = 1
GRAPE_VERSION = '0.9.0-django'
GRAPE_SRV_NAME = 'Grape'

# Recaptcha (leave empty to disable)
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''

# Password hashers - support PHP bcrypt ($2y$) and Django bcrypt ($2b$)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'grape.hashers.GrapeBcryptHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
