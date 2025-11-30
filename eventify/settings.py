import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Simple environment variable loader
def get_env_variable(key, default=None):
    """
    Get environment variable from .env file or system environment
    """
    # Try to read from .env file first
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key_val = line.split('=', 1)
                    if len(key_val) == 2 and key_val[0].strip() == key:
                        return key_val[1].strip()
    
    # Fallback to system environment
    return os.environ.get(key, default)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('SECRET_KEY', 'django-insecure-dev-key-1234567890abcdef')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = get_env_variable('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'events',
    'users', 
    'bookings',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eventify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eventify.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (Uploaded images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# M-Pesa Configuration (with development defaults)
MPESA_CONSUMER_KEY = get_env_variable('MPESA_CONSUMER_KEY', 'test_consumer_key_dev')
MPESA_CONSUMER_SECRET = get_env_variable('MPESA_CONSUMER_SECRET', 'test_consumer_secret_dev')
MPESA_SHORTCODE = get_env_variable('MPESA_SHORTCODE', '174379')
MPESA_PASSKEY = get_env_variable('MPESA_PASSKEY', 'test_passkey_dev')
MPESA_CALLBACK_URL = get_env_variable('MPESA_CALLBACK_URL', 'https://example.com/callback')