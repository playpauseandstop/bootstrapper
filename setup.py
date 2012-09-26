#!/usr/bin/env python

import imp
import os
import sys

from distutils.core import setup


DIRNAME = os.path.abspath(os.path.dirname(__file__))
rel = lambda *parts: os.path.abspath(os.path.join(DIRNAME, *parts))

kwargs = \
    {'install_requires': ['argparse']} if sys.version_info < (2, 7) else {}

handler = open(rel('README.rst'))
README = handler.read()
handler.close()

module = imp.load_source('bootstrapper', rel('bootstrapper'))
version = module.__version__
os.unlink(rel('bootstrapperc'))

setup(
    name='bootstrapper',
    version=version,
    description='Bootstrap Python projects with virtualenv and pip.',
    long_description=README,
    author='Igor Davydenko',
    author_email='playpauseandstop@gmail.com',
    url='https://github.com/playpauseandstop/bootstrapper',
    scripts=['bootstrapper'],
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: System :: Systems Administration',
    ],
    keywords='bootstrap pip virtualenv',
    license='BSD License',
    **kwargs
)
