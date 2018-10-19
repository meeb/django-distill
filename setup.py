# -*- coding: utf-8 -*-

import os
import sys
from setuptools import (setup, find_packages)


version = 1.5


with open('README.md', 'rt') as f:
    long_description = f.read()


with open('requirements.txt', 'rt') as f:
    requirements = tuple(f.read().split())


setup(
    name = 'django-distill',
    version = str(version),
    url = 'https://github.com/mgrp/django-distill',
    author = 'the m group, https://m.pr/',
    author_email = 'hi@m.pr',
    description = 'Static site renderer and publisher for Django.',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    license = 'MIT',
    include_package_data = True,
    install_requires = requirements,
    packages = find_packages(),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords = ('django', 'distill', 'static', 's3', 'rackspace',
                'google cloud storage'),
)

# eof
