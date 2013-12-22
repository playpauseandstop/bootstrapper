#!/usr/bin/env python

from __future__ import print_function

import copy
import operator
import os
import platform
import subprocess
import sys
import traceback

try:
    from configparser import Error as ConfigParserError, SafeConfigParser
except ImportError:
    from ConfigParser import Error as ConfigParserError, SafeConfigParser

from collections import defaultdict
from distutils.util import strtobool


__author__ = 'Igor Davydenko'
__license__ = 'BSD License'
__script__ = 'bootstrapper'
__version__ = '0.2.1'


CONFIG = {
    __script__: {
        'env': 'env',
        'requirements': 'requirements.txt',
        'quiet': False,
    },
    'pip': {
        'download_cache': os.path.expanduser(
            os.path.join('~', '.{0}'.format(__script__), 'pip-cache')
        ),
    },
    'virtualenv': {},
}
DEFAULT_CONFIG = 'bootstrap.cfg'
IS_PY3 = sys.version_info[0] == 3
IS_WINDOWS = platform.system() == 'Windows'

iteritems = lambda seq: seq.items() if IS_PY3 else seq.iteritems()
iterkeys = lambda seq: seq.keys() if IS_PY3 else seq.iterkeys()
string_types = (bytes, str) if IS_PY3 else basestring


def check_pre_requirements(pre_requirements):
    """
    Check all necessary system requirements to exist.
    """
    pre_requirements = set(pre_requirements or [])
    pre_requirements.add('virtualenv')

    for requirement in pre_requirements:
        if not which(requirement):
            error('Requirement {0!r} is not found in system'.
                  format(requirement))

    return True


def config_to_args(config):
    """
    Convert config dict to arguments list.
    """
    result = []

    for key, value in iteritems(config):
        if value is False:
            continue

        key = key.replace('_', '-')

        if value is not True:
            result.append('--{0}={1}'.format(key, str(value)))
        else:
            result.append('--{0}'.format(key))

    return result


def create_env(env, args, recreate=False, quiet=False):
    """
    Create virtual environment.
    """
    cmd = None

    if not quiet:
        print('== Step 1. Create virtual environment ==')

    if recreate or not os.path.isdir(env):
        cmd = 'virtualenv {0} {1}'.format(args, env)

    if not cmd and not quiet:
        print('Virtual environment {0!r} already created, done...'.format(env))

    if cmd:
        run_cmd(cmd, echo=not quiet)

    if not quiet:
        print()

    return True


def error(message, code=None):
    """
    Print error message and exit with error code.
    """
    print('ERROR: {0}. Exit...'.format(message.rstrip('.')))
    sys.exit(code or 1)


def install(env, requirements, args, quiet=False):
    """
    Install library or project into virtual environment.
    """
    if os.path.isfile(requirements):
        args += ' -r {0}'.format(requirements)
        label = 'project'
    else:
        args += ' -e .'
        label = 'library'

    if not quiet:
        print('== Step 2. Install {0} =='.format(label))

    pip_cmd(env, 'install {0}'.format(args), echo=not quiet)

    if not quiet:
        print()

    return True


def main(*args):
    """
    Bootstrap Python projects and libraries with virtualenv and pip.

    Also check system requirements before bootstrap and run post bootstrap
    hook if any.
    """
    try:
        # Create parser, read arguments from direct input or command line
        args = parse_args(args or sys.argv[1:])

        # Initialize bootstrapper instance Read current config from file
        config = read_config(args.config, args)
        bootstrap = config[__script__]

        # Check pre-requirements
        check_pre_requirements(bootstrap['pre_requirements'])

        # Create virtual environment
        env_args = prepare_args(config['virtualenv'], bootstrap)
        create_env(bootstrap['env'],
                   env_args,
                   bootstrap['recreate'],
                   bootstrap['quiet'])

        # And install library or project here
        pip_args = prepare_args(config['pip'], bootstrap)
        install(bootstrap['env'],
                bootstrap['requirements'],
                pip_args,
                bootstrap['quiet'])

        # Run post-bootstrap hook
        run_hook(bootstrap['hook'], bootstrap, bootstrap['quiet'])

        # All OK!
        if not bootstrap['quiet']:
            print('All OK!')
    except BaseException as err:
        filename = os.path.expanduser(
            os.path.join('~',
                         '.{0}'.format(__script__),
                         '{0}.log'.format(__script__))
        )

        with open(filename, 'a+') as handler:
            traceback.print_exc(file=handler)

        message = ('User aborted workflow'
                   if isinstance(err, KeyboardInterrupt)
                   else 'Unexpected error catched')
        print('ERROR: {0}. Exit...'.format(message), file=sys.stderr)
        print('Full log stored to ~/.{0}/{0}.log'.format(__script__),
              file=sys.stderr)

        # True means error happened, exit code: 1
        return True

    # False means everything went alright, exit code: 0
    return False


def parse_args(args):
    """
    Parse args from command line by creating argument parser instance and
    process it.
    """
    from argparse import ArgumentParser

    description = ('Bootstrap Python projects and libraries with virtualenv '
                   'and pip.')
    parser = ArgumentParser(description=description)
    parser.add_argument('--version', action='version', version=__version__)

    parser.add_argument(
        '-c', '--config', default=DEFAULT_CONFIG,
        help='Path to config file. By default: {0}'.format(DEFAULT_CONFIG)
    )
    parser.add_argument(
        '-p', '--pre-requirements', default=[], nargs='+',
        help='List of pre-requirements to check, separated by space.'
    )
    parser.add_argument(
        '-e', '--env',
        help='Virtual environment name. By default: {0}'.
             format(CONFIG[__script__]['env'])
    )
    parser.add_argument(
        '-r', '--requirements',
        help='Path to requirements file. By default: {0}'.
             format(CONFIG[__script__]['requirements']))
    parser.add_argument(
        '-C', '--hook', help='Execute this hook after bootstrap process.'
    )
    parser.add_argument(
        '--recreate', action='store_true',
        help='Recreate virtualenv on every run.'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help='Minimize output, show only error messages.'
    )

    return parser.parse_args(args)


def pip_cmd(venv, cmd, **kwargs):
    """
    Run pip command in given virtual environment.
    """
    prefix = ''

    if IS_WINDOWS:
        prefix = 'python '
        pip_path = os.path.join(venv, 'Scripts', 'pip-script.py')
    else:
        pip_path = os.path.join(venv, 'bin', 'pip')

    return run_cmd('{0}{1} {2}'.format(prefix, pip_path, cmd), **kwargs)


def prepare_args(config, bootstrap):
    """
    Convert config dict to command line args line.
    """
    config = copy.deepcopy(config)
    environ = dict(copy.deepcopy(os.environ))

    data = {'env': bootstrap['env'],
            'requirements': bootstrap['requirements']}
    environ.update(data)

    if isinstance(config, string_types):
        return config.format(**environ)

    for key, value in iteritems(config):
        if not isinstance(value, string_types):
            continue
        config[key] = value.format(**environ)

    return ' '.join(config_to_args(config))


def read_config(filename, args):
    """
    Read and parse configuration file. By default, ``filename`` is relative
    path to current work directory.

    If no config file found, default ``CONFIG`` would be used.
    """
    # Initial vars
    config = defaultdict(dict)
    converters = {
        __script__: {
            'pre_requirements': operator.methodcaller('split', ' ')
        },
    }
    default = copy.deepcopy(CONFIG)
    sections = set(iterkeys(default))

    # Expand user and environ vars in config filename
    filename = os.path.expandvars(os.path.expanduser(filename))

    # Read config if it exists on disk
    if os.path.isfile(filename):
        parser = SafeConfigParser()

        try:
            parser.read(filename)
        except ConfigParserError:
            error('Cannot parse config file at {0!r}'.format(filename))

        # Apply config for each possible section
        for section in sections:
            if not parser.has_section(section):
                continue

            items = parser.items(section)

            # Make auto convert here for integers and boolean values
            for key, value in items:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    try:
                        value = bool(strtobool(value))
                    except ValueError:
                        pass

                if section in converters and key in converters[section]:
                    value = converters[section][key](value)

                config[section][key] = value

    # Update config with default values if necessary
    for section, data in iteritems(default):
        if section not in config:
            config[section] = data
        else:
            for key, value in iteritems(data):
                config[section].setdefault(key, value)

    # Update bootstrap config from parsed args
    keys = set((
        'env', 'hook', 'pre_requirements', 'quiet', 'recreate', 'requirements'
    ))

    for key in keys:
        value = getattr(args, key)
        config[__script__].setdefault(key, value)

        if value is not None or (key == 'pre_requirements' and value):
            config[__script__][key] = value

    return config


def run_cmd(cmd, call=True, echo=False, fail_silently=False):
    """
    Run command with ``subprocess`` module and return output as result.
    """
    if sys.version_info < (2, 7):
        alt_retcode = True
        check_output = subprocess.check_call
    else:
        alt_retcode = False
        check_output = subprocess.check_output

    kwargs = {'shell': True}
    method = subprocess.call if call else check_output
    stdout = sys.stdout if echo else subprocess.PIPE

    if echo:
        print('$ {0}'.format(cmd))

    if call:
        kwargs.update({'stdout': stdout})

    try:
        retcode = method(cmd, **kwargs)
    except subprocess.CalledProcessError as err:
        if fail_silently:
            return False
        error(str(err) if IS_PY3 else unicode(err))

    if call and retcode and not fail_silently:
        error('Command {0!r} returned non-zero exit status {1}'.
              format(cmd, retcode))

    return not retcode if alt_retcode else retcode


def run_hook(hook, config, quiet=False):
    """
    Run post-bootstrap hook if any.
    """
    if not hook:
        return True

    if not quiet:
        print('== Step 3. Run post-bootstrap hook ==')

    run_cmd(prepare_args(hook, config),
            echo=not quiet,
            fail_silently=True)

    if not quiet:
        print()

    return True


def which(executable):
    """
    Shortcut to check whether executable available in current environment or
    not.
    """
    cmd = 'where' if IS_WINDOWS else 'which'
    return run_cmd(' '.join((cmd, executable)), call=False, fail_silently=True)


if __name__ == '__main__':
    sys.exit(int(main()))
