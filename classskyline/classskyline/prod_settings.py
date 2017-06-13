# -*- coding: utf-8 -*-
###########
# 生产环境 #
###########
from settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
TEMPLATE_DEBUG = False
ALLOWED_HOSTS = ['*']

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
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': os.path.join(BASE_DIR, 'log', 'classskyline.log'),
            'maxBytes': 50 * 1024 * 1024,
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO',
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
        },
        'requests.packages.urllib3': {
            'handlers': ['file'],
            'level': 'WARNING',
        }
    },
}

# 此处设置注意跟安装脚本保持一致
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'classskyline',
        'USER': 'root',#'classskyline',
        'PASSWORD': 'thsoft',#'1Q2W3E4R5T6y7u8i9o0p-[=]',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

#启动时用不同的配置文件
#python manage.py migrate --settings=classskyline.prod_settings
