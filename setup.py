# -*- coding: utf-8 -*-

import os
import sys
from setuptools import (setup, find_packages)


version = 1.0


setup(
    name='django-distill',
    version=str(version),
    url='https://github.com/mgrp/django-distill',
    download_url='https://github.com/mgrp/django-distill/tarball/0.6',
    author='the m group, https://m.pr/',
    author_email='hi@m.pr',
    description=('Static site renderer and publisher for Django.'),
    license='MIT',
    include_package_data=True,
    install_requires=('django', 'requests'),
    packages=find_packages(),
    classifiers=[
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
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords=('django', 'distill', 'static', 's3', 'rackspace',
              'google cloud storage'),
)

# eof
