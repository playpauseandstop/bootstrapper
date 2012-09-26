#!/usr/bin/env python

import os
import sys
import subprocess
import tempfile

from distutils.core import setup


DIRNAME = os.path.abspath(os.path.dirname(__file__))
kwargs = \
    {'install_requires': ['argparse']} if sys.version_info < (2, 7) else {}

handler = open(os.path.join(DIRNAME, 'README.rst'))
README = handler.read()
handler.close()

handler = tempfile.TemporaryFile()
code = subprocess.check_call('{0}/bootstrapper --version'.format(DIRNAME),
                             shell=True,
                             stderr=handler)
handler.seek(0)
version = handler.read().strip()
handler.close()

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
