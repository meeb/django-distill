import os
import sys
from setuptools import setup, find_packages


version = '3.2.0'


with open('README.md', 'rt') as f:
    long_description = f.read()


with open('requirements.txt', 'rt') as f:
    requirements = tuple(f.read().split())


setup(
    name = 'django-distill',
    version = version,
    url = 'https://github.com/meeb/django-distill',
    author = 'https://github.com/meeb',
    author_email = 'meeb@meeb.org',
    description = 'Static site renderer and publisher for Django.',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    license = 'MIT',
    include_package_data = True,
    install_requires = requirements,
    extras_require = {
        'amazon': ['boto3'],
        'google': ['google-api-python-client', 'google-cloud-storage'],
        'microsoft': ['azure-storage-blob'],
    },
    packages = find_packages(),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords = ['django', 'distill', 'static', 'website', 'jamstack', 's3',
                'amazon s3', 'aws', 'amazon', 'google', 'microsoft',
                'google cloud', 'google cloud storage', 'azure',
                'azure storage', 'azure blob storage'],
)
