# -*- coding: utf-8 -*-


import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SECRET_KEY = 'test'


ROOT_URLCONF = 'tests.urls'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join('BASE_DIR' , 'test.sqlite3'),
    }
}


INSTALLED_APPS = [
    'tests',
]


# eof
