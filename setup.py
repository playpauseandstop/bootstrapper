#!/usr/bin/env python

import os
import re
import sys

from setuptools import setup


DIRNAME = os.path.abspath(os.path.dirname(__file__))


def rel(*parts):
    return os.path.abspath(os.path.join(DIRNAME, *parts))


with open(rel('README.rst')) as readme_file:
    README = readme_file.read()

with open(rel('bootstrapper.py')) as bootstrapper_file:
    INIT_PY = bootstrapper_file.read()

IS_PY26 = sys.version_info[:2] == (2, 6)
VERSION = re.findall("__version__ = '([^']+)'", INIT_PY)[0]


setup(
    name='bootstrapper',
    version=VERSION,
    description='Bootstrap Python projects with virtualenv and pip.',
    long_description=README,
    author='Igor Davydenko',
    author_email='playpauseandstop@gmail.com',
    url='https://github.com/playpauseandstop/bootstrapper',
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Systems Administration',
    ],
    keywords='bootstrap pip virtualenv',
    license='BSD License',
    entry_points={
        'console_scripts': [
            'bootstrapper=bootstrapper:main',
        ]
    },
    install_requires=list(filter(None, [
        'argparse>=1.3.0' if IS_PY26 else None,
        'virtualenv>=1.10',
    ])),
    py_modules=[
        'bootstrapper'
    ],
    test_suite='tests',
    tests_require=list(filter(None, [
        'unittest2==0.5.1' if IS_PY26 else None,
    ]))
)
