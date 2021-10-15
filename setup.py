#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages


with open('README.rst') as readme_file:
    readme = readme_file.read()


setup(
    name='django-celery-extensions',
    long_description=readme,
    long_description_content_type='text/markdown',
    version='0.0.24',
    description="Django celery extensions library.",
    keywords='django, celery',
    author='Lubos Matl',
    author_email='matllubos@gmail.com',
    url='https://github.com/druids/django-celery-extensions',
    license='MIT',
    package_dir={'django_celery_extensions': 'django_celery_extensions'},
    include_package_data=True,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Czech',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
    ],
    install_requires=[
        'django >= 2.2.14',
        'import_string >= 0.1.0',
        'celery >= 5.0.5',
        'attrdict >= 2.0.0',
    ],
    zip_safe=False
)
