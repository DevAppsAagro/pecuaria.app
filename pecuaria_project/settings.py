"""
Django settings for pecuaria_project project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.FazendaAtualMiddleware',  # Adiciona o middleware da fazenda atual
    'core.middleware.SubscriptionMiddleware',  # Middleware de verificação de assinatura
]

ROOT_URLCONF = 'pecuaria_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'core', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.debug',
                'core.context_processors.supabase_config',  # Novo context processor
            ],
        },
    },
]

WSGI_APPLICATION = 'pecuaria_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'core', 'static'),
        os.path.join(BASE_DIR, 'public'),
    ]
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
else:
    # Em produção (Vercel), os arquivos estáticos são servidos da pasta static
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Configuração de MIME types
MIMETYPES = {
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CORS_ALLOW_ALL_ORIGINS = True  # Apenas para desenvolvimento
CORS_ALLOW_CREDENTIALS = True

# Auth settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Configurações do Stripe
# Nota: A integração com Eduzz foi removida e o sistema utiliza exclusivamente o Stripe para pagamentos
STRIPE_API_BASE = config('STRIPE_API_BASE', default='https://api.stripe.com')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_...')  # Substituir pela sua chave secreta
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='pk_test_...')  # Substituir pela sua chave pública
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='whsec_...')  # Substituir pelo secret do webhook
STRIPE_WEBHOOK_URL = config('STRIPE_WEBHOOK_URL', default='https://app.pecuaristapro.com/api/stripe/webhook/')
STRIPE_MENSAL_PRICE_ID = config('STRIPE_MENSAL_PRICE_ID', default='price_...')  # ID do preço mensal
STRIPE_ANUAL_PRICE_ID = config('STRIPE_ANUAL_PRICE_ID', default='price_...')  # ID do preço anual

# Email settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Pecuária.app <noreply@pecuaristapro.com>')

# Base URL for links in emails
BASE_URL = config('BASE_URL', default='https://app.pecuaristapro.com')

# Configuração de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# Supabase Settings
SUPABASE_URL = config('SUPABASE_URL')
SUPABASE_KEY = config('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = config('SUPABASE_SERVICE_KEY')  # Para operações administrativas

# Storage settings
SUPABASE_STORAGE_BUCKET = 'profile-photos'  # Bucket para fotos de perfil
SUPABASE_RECEIPTS_BUCKET = 'payment-receipts'  # Bucket para comprovantes
SUPABASE_FARM_LOGOS_BUCKET = 'logofazenda'  # Bucket para logos de fazendas
SUPABASE_BOLETOS_BUCKET = 'boletoecomprovante'  # Bucket para boletos e comprovantes

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
