# -*- coding: utf-8 -*-
###########
# 测试环境 #
###########

"""
Django settings for classskyline project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SITE_DIR = os.path.dirname(BASE_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '3hv_hdln_avvlz+*)@wt02x*nysf6o^yb7yn*4$!u3x-fht27q'

DEBUG = True
TEMPLATE_DEBUG = True
ALLOWED_HOSTS = []

LOGIN_URL = '/login'

# Application definition

INSTALLED_APPS = (
    # 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'classskyline',
    'api',
    'common',
    'cloudclass',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'cloudclass.middlewares.InitCheckMiddleware'
)

ROOT_URLCONF = 'classskyline.urls'

WSGI_APPLICATION = 'classskyline.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(SITE_DIR, "static")

TEMPLATE_DIRS = (
    'templates',
    'cloudclass/templates',
)

STATICFILES_DIRS = (
    'static',
    'cloudclass/static',
)

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

DEFAULT_DESKTOP_PREFIX = 'stu'
DEFAULT_THREAD_COUNT = 10
DEFAULT_STORAGE_POOL = {
    "defaultpool": "/vms/images"
}

ISOS_PATH = '/vms/isos'

FTP_TMPT = "hccftp://{username}:{password}@{ip}/{path}"
FTP_CONF = {
    'images': {'username': 'ftpuser', 'password': 'ftpuser', 'path': 'images'},
    'isos': {'username': 'ftpuser', 'password': 'ftpuser', 'path': 'isos' },
    'soft': {'username': 'ftpuser', 'password': 'ftpuser', 'path': 'share'},
    'upgrade': {'username': 'upgradeuser', 'password': 'upgradeuser', 'path': ''}
}

DEFAULT_SHARE_IMAGE = {
    "defaultdir": "/vms/share",
    "defaultvolume": "/vms/isos/share.img"
}
VIRT_DRIVER = 'cloudapi.casapi.driver.CasDriver'
STACK_BACKENDS = {
    'cas': {  # CAS RESTful API
        'AUTH_URL': 'http://10.88.16.99:8080',
        'USERNAME': 'admin',
        'PWD': 'admin',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(levelname)s]%(lineno)d %(filename)s/%(funcName)s %(asctime)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }

    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': os.path.join(BASE_DIR, 'log', 'classskyline.log'),
            'maxBytes': 100 * 1024 * 1024,  # 100M
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'sh.command': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'sh.streamreader': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'sh.stream_bufferer': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'sh.process': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
        'sh.streamwriter': {
            'handlers': ['file'],
            'level': 'WARNING',
        }
    },
}

LOGIN_REDIRECT_URL = '/cloudclass/'
PRELOAD_IMAGE_DIR = '/dev/shm'
COURSE_USING_TMPFS = False
DESKTOP_USING_TMPFS = False

DEFAULT_HOSTPOOL_NAME = 'hccpool'
DEFAULT_VSWITCH_NAME = 'vswitch1'
# cas network policy profile name
DEFAULT_NPP_NAME = 'Default'
# cas acl policy name
DEFAULT_ACL_NAME = 'defaultacl'

FIREWALL_WHITELIST = ['192.168.100.0/24', '192.168.200.0/24']
# SAMBA config
WORKSPACEROOT = '/opt/doc'

MEDIA_ROOT = os.path.join(BASE_DIR).replace('//', '/')
