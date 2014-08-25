#!/usr/bin/env python

import os
import re
import sys

from setuptools import setup


DIRNAME = os.path.abspath(os.path.dirname(__file__))
rel = lambda *parts: os.path.abspath(os.path.join(DIRNAME, *parts))

with open(rel('README.rst')) as readme_file:
    README = readme_file.read()

with open(rel('bootstrapper.py')) as bootstrapper_file:
    INIT_PY = bootstrapper_file.read()

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
        'Development Status :: 4 - Beta',
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
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: System :: Systems Administration',
    ],
    keywords='bootstrap pip virtualenv',
    license='BSD License',
    entry_points={
        'console_scripts': [
            'bootstrapper=bootstrapper:main',
            'bootstrapper-{0}.{1}=bootstrapper:main'.
            format(*sys.version_info[:2]),
        ]
    },
    install_requires=list(filter(None, [
        'argparse==1.2.1' if sys.version_info[:2] < (2, 7) else None,
        'virtualenv>=1.10',
    ])),
    py_modules=[
        'bootstrapper'
    ],
    test_suite='tests',
    tests_require=list(filter(None, [
        'unittest2==0.5.1' if sys.version_info[:2] < (2, 7) else None,
    ]))
)
