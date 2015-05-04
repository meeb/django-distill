# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup
from django_distill import __version__ as version

def fread(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-distill',
    version=str(version),
    url='https://github.com/mgrp/django-distill',
    author='the m group, https://m.pr/',
    author_email='hi@m.pr',
    description=('Static site renderer and publisher for Django.'),
    license='MIT',
    include_package_data=True,
    install_requires = ('requests',)
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords = ['django', 'distill',],
)

# eof
