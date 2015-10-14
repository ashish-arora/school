"""
Django settings for school project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'm&i^tg-g2g^dm805_ftv1=78tw35+ac3d*@0v9&=a63oc#k8qb'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_mongoengine',
    'rest_framework_swagger',
    'mongoengine.django.mongo_auth',
    'schoolapp',
    'gcm',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'school.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
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

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': 'localhost:6379',
        #'LOCATION': '54.254.167.4:6379',
        'OPTIONS': {
            'DB': 1,
            'PASSWORD': '',
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
    },
}

LOGGING = {
    'version': 1,
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers':['console'],
            'propagate': True,
            'level':'DEBUG',
        }
    },
}


#REDIS_CONN = redis.StrictRedis(host='54.254.167.4')

REDIS_CONN = redis.StrictRedis()

WSGI_APPLICATION = 'school.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

from mongoengine import connect
#connect('schooldb', host='54.254.167.4')
connect('schooldb', host='127.0.0.1')

AUTH_USER_MODEL = 'mongo_auth.MongoUser'
#MONGOENGINE_USER_DOCUMENT = 'mongoengine.django.auth.User'
MONGOENGINE_USER_DOCUMENT = 'schoolapp.models.CustomUser'


AUTHENTICATION_BACKENDS = (
    'mongoengine.django.auth.MongoEngineBackend'
)
SESSION_ENGINE = 'mongoengine.django.sessions'


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

####### Queues ########
NOTIFICATION_QUEUE = 'notification'
SMS_QUEUE = 'sms'
STATUS_UPDATE_QUEUE="status-update"

###### JABBER SETTINGS ##########
ADMIN_JID=''
JABBER_SERVER='127.0.0.1'
ADMIN_JABBER_PASSWORD=''
JABBER_PORT=5222

#### PNS ########
#TODO: Register with Google Cloud Messaging from GOOGLE API Console
GCM_QUEUE = "gcm_queue"
GCM_APIKEY = "<api_key>"
GCM_PROJECT_ID = "<gcm_project_id>"

#### Sms host ####
ssd_sender_id = 'SCCHAP'
smsgw_ssd_url = 'http://sms.ssdindia.com/api/sendhttp.php'
ssd_auth_key = '9218AIpGhQJkUvJc55f57357'

amazon_s3_config={'staging':{'status_upload_store': 'status-staging-upload-store'}, 'prod': {'status_upload_store': 'status-prod-upload-store'}}


AWS_ACCESS_KEY_ID = 'AKIAIKMAQXKFTMLDRSJA'
AWS_SECRET_ACCESS_KEY = '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'
S3_CONTENT_BUCKET = 'S3_CONTENT_BUCKET'
#FILE_EXPIRY_TIME = int(604800)#7*24*3600
#FILE_EXPIRY_DELTA = 2 #in hrs
STATUS_UPLOAD_STORE = amazon_s3_config['staging']['status_upload_store']
#IMAGE_UPLOAD_STORE = amazon_s3_config['staging']['status_upload_store']

MEDIA_ROOT='/var/media/'

MEDIA_URL='/var/media/'

