============
bootstrapper
============

Bootstrap Python projects by creating virtual environment, installing all
requirements there and execute post-bootstrap hooks if any.

Also supported creating virtual environments not only for default
requirements file (named *major*, by default: ``requirements.txt``), but
for any other files (named *minor*), which matched mask
``requirements-(.*).txt``, where ``requirements`` and ``txt`` could be
changed manually if not default requirements file would be used.

Requirements
============

* `Python <http://www.python.org/>`_ 2.6 or 2.7
* `virtualenv <http://www.virtualenv.org/>`_ 1.7 or higher
* `argparse <http://pypi.python.org/pypi/argparse>`_ (*optional*, only
  needed for Python 2.6)
* `virtualenv-clone <http://pypi.python.org/pypi/virtualenv-clone>`_
  (*optional*, needed only when you want to create virtual environments for
  minor requirements as copy of major virtual environment)

Installation
============

As easy as::

    # pip install bootstrapper

License
=======

``bootstrapper`` is licensed under the `BSD License
<https://github.com/playpauseandstop/bootstrapper/blob/master/LICENSE>`_.

Configuration
=============

You may configure any option of ``bootstrapper``, ``virtualenv`` and ``pip``
by setting it in ``bootstrap.cfg`` file. For example::

    [bootstrapper]
    copy_virtualenv = True

    [pip]
    quiet = True

    [virtualenv]
    system_site_packages = True
    quiet = True

By default, next configuration would be used::

    [pip]
    download_cache = {env}/src/

    [virtualenv]
    distribute = True

So, if you not rewrite this options they would be auto-added to your
configuration. Also, all bootstrap configuration would be overwrited by
values from command line.

Usage
=====

::

    $ bootstrapper --help
    usage: bootstrapper [-h] [-v] [-c CONFIG] [-e ENV] [-r REQUIREMENTS]
                    [-p PRE_REQUIREMENTS [PRE_REQUIREMENTS ...]] [-C HOOK]
                    [-H] [--copy-virtualenv] [--recreate-virtualenv]
                    [--only-major] [-q]
                    [dest]

    Bootstrap Python projects with virtualenv and pip.

    positional arguments:
      dest                  Bootstrap project using only this minor requirements.
                            By default major requirements file and all minor files
                            would be used for bootstrapping.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -c CONFIG, --config CONFIG
                            Path to config file. By default: bootstrap.cfg
      -e ENV, --env ENV     Name of major virtual environment. By default: env
      -r REQUIREMENTS, --requirements REQUIREMENTS
                            Path to major requirements file. By default:
                            requirements.txt
      -p PRE_REQUIREMENTS [PRE_REQUIREMENTS ...], --pre-requirements PRE_REQUIREMENTS [PRE_REQUIREMENTS ...]
                            List pre-requirements to check separated by space.
      -C HOOK, --hook HOOK  Execute this hook after bootstrap process.
      -H, --hook-all        Execute HOOK in each virtualenv, not only in major
                            one.
      --copy-virtualenv     Create virtualenv for minor requirements by copying
                            major virtualenv. NOTE: If minor venv already exists
                            copy process would be aborted to avoid "dest dir
                            exists" error.
      --recreate-virtualenv
                            Recreate virtualenv each time, does not care about
                            exists of env at disk.
      --only-major          Create only major virtual environment, ignore all
                            other requirements files.
      -q, --quiet           Minimize output, show only error messages.

Examples
========

Project case
------------

In common only one requirements file exists in the project, and for most
cases something like ``settings_local.py.def`` should be copied to proper
location after creating virtual environment and installing requirements. So,
project tree could look this::

    .
    ├── README.rst
    ├── requirements.txt
    └── project
        ├── __init__.py
        ├── app.py
        ├── static
        ├── templates
        ├── settings.py
        ├── settings_local.py.def
        ├── tests.py
        └── views.py

In that case you can easilly bootstrap project with::

    $ bootstrapper -C 'cp -n project/settings_local.py{{.def,}}'

This will create ``env/`` virtual environment, install there all requirements
from ``requirements.txt`` and finally copy default file to
``settings_local.py`` if it not exists.

Application case
----------------

For applications otherwise it's good idea to have several requirements files,
to support testing on different requirement versions. For example, next
application has default requirements and requirements for ``Flask==0.8``,

::

    .
    ├── README.rst
    └── application
        └── ...
    ├── setup.py
    └── testapp
        ├── app.py
        ├── requirements.txt
        ├── requirements-0.8.txt
        ├── tests.py
        └── views.py

And in that case bootstrapping test app would be looking like::

    $ cd testapp/ && bootstrapper

This will create ``env/`` and ``env-0.8/`` environments and install there
requirements from ``requirements.txt`` and ``requirements-0.8.txt`` apparently.

In case if you want to create/update enviroment only for ``0.8`` minor
requirement, you need to::

    $ cd testapp/ && bootstrapper 0.8

More examples
-------------

Bootstrapper used in next my open source projects:

* `Learn Python <https://github.com/playpauseandstop/learnpython.in.ua>`_
* `Flask-Dropbox <https://github.com/playpauseandstop/Flask-Dropbox>`_
* `Flask-And-Redis <https://github.com/playpauseandstop/Flask-And-Redis>`_

Changelog
=========

0.1.1
-----

+ Use ``--use-mirrors`` key by default when ``pip`` installs requirements to
  virtual environment.

0.1
---

- Initial release.
