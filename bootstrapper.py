"""
============
bootstrapper
============

Bootstrap Python projects or libraries with ease.

"""

from __future__ import print_function

import copy
import operator
import os
import platform
import subprocess
import sys
import tempfile
import traceback

try:
    from configparser import Error as ConfigParserError, ConfigParser
except ImportError:
    from ConfigParser import (
        Error as ConfigParserError,
        SafeConfigParser as ConfigParser,
    )

from collections import defaultdict
from contextlib import contextmanager
from distutils.util import strtobool
from functools import wraps

import pip

try:
    from pip.log import _color_wrap
    from pip._vendor import colorama
except ImportError:
    colorama = None


__author__ = 'Igor Davydenko'
__license__ = 'BSD License'
__script__ = 'bootstrapper'
__version__ = '1.0.dev0'


BOOTSTRAPPER_TEST_KEY = 'BOOTSTRAPPER_TEST'
CONFIG = {
    __script__: {
        'env': 'env',
        'requirements': 'requirements.txt',
        'quiet': False,
    },
    'pip': {},
    'virtualenv': {},
}
DEFAULT_CONFIG = 'bootstrap.cfg'
ERROR_HANDLER_DISABLED = False

IS_PY3 = sys.version_info[0] == 3
IS_WINDOWS = platform.system() == 'Windows'

string_types = (str, ) if IS_PY3 else (basestring, )  # noqa


def check_pre_requirements(pre_requirements):
    """Check all necessary system requirements to exist.

    :param pre_requirements:
        Sequence of pre-requirements to check by running
        ``where <pre_requirement>`` on Windows and ``which ...`` elsewhere.
    """
    pre_requirements = set(pre_requirements or [])
    pre_requirements.add('virtualenv')

    for requirement in pre_requirements:
        if not which(requirement):
            print_error('Requirement {0!r} is not found in system'.
                        format(requirement))
            return False

    return True


def config_to_args(config):
    """Convert config dict to arguments list.

    :param config: Configuration dict.
    """
    result = []

    for key, value in iteritems(config):
        if value is False:
            continue

        key = '--{0}'.format(key.replace('_', '-'))

        if isinstance(value, (list, set, tuple)):
            for item in value:
                result.extend((key, smart_str(item)))
        elif value is not True:
            result.extend((key, smart_str(value)))
        else:
            result.append(key)

    return tuple(result)


def create_env(env, args, recreate=False, ignore_activated=False, quiet=False):
    """Create virtual environment.

    :param env: Virtual environment name.
    :param args: Pass given arguments to ``virtualenv`` script.
    :param recerate: Recreate virtual environment? By default: False
    :param ignore_activated:
        Ignore already activated virtual environment and create new one. By
        default: False
    :param quiet: Do not output messages into terminal. By default: False
    """
    cmd = None
    result = True

    inside_env = hasattr(sys, 'real_prefix') or os.environ.get('VIRTUAL_ENV')
    env_exists = os.path.isdir(env)

    if not quiet:
        print('== Step 1. Create virtual environment ==')

    if (
        recreate or (not inside_env and not env_exists)
    ) or (
        ignore_activated and not env_exists
    ):
        cmd = ('virtualenv', ) + args + (env, )

    if not cmd and not quiet:
        if inside_env:
            message = 'Working inside of virtual environment, done...'
        else:
            message = 'Virtual environment {0!r} already created, done...'
        print(message.format(env))

    if cmd:
        with disable_error_handler():
            result = not run_cmd(cmd, echo=not quiet)

    if not quiet:
        print()

    return result


@contextmanager
def disable_error_handler():
    """Context manager to temporary disable error handling."""
    global ERROR_HANDLER_DISABLED
    ERROR_HANDLER_DISABLED = True
    yield
    ERROR_HANDLER_DISABLED = False


def error_handler(func):
    """Decorator to error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Run actual function and if exception catched and error handler enabled
        put traceback to log file
        """
        try:
            return func(*args, **kwargs)
        except BaseException as err:
            # Do not catch exceptions on testing
            if BOOTSTRAPPER_TEST_KEY in os.environ:
                raise
            # Fail silently if error handling disabled
            if ERROR_HANDLER_DISABLED:
                return True
            # Otherwise save traceback to log
            return save_traceback(err)
    return wrapper


def get_temp_streams():
    """Return two temporary file handlers for STDOUT and STDERR."""
    kwargs = {'encoding': 'utf-8'} if IS_PY3 else {}
    return (tempfile.TemporaryFile('w+', **kwargs),
            tempfile.TemporaryFile('w+', **kwargs))


def install(env, requirements, args, ignore_activated=False,
            install_dev_requirements=False, quiet=False):
    """Install library or project into virtual environment.

    :param env: Use given virtual environment name.
    :param requirements: Use given requirements file for pip.
    :param args: Pass given arguments to pip script.
    :param ignore_activated:
        Do not run pip inside already activated virtual environment. By
        default: False
    :param install_dev_requirements:
        When enabled install prefixed or suffixed dev requirements after
        original installation process completed. By default: False
    :param quiet: Do not output message to terminal. By default: False
    """
    if os.path.isfile(requirements):
        args += ('-r', requirements)
        label = 'project'
    else:
        args += ('-U', '-e', '.')
        label = 'library'

    if not quiet:
        print('== Step 2. Install {0} =='.format(label))

    result = not pip_cmd(env,
                         ('install',) + args,
                         ignore_activated,
                         echo=not quiet)

    if not quiet:
        print()

    # Attempt to install development requirements
    if install_dev_requirements and label == 'project' and result:
        dev_requirements = None
        dirname = os.path.dirname(requirements)
        basename, ext = os.path.splitext(os.path.basename(requirements))

        # Possible dev requirements files:
        #
        # * <requirements>-dev.<ext>
        # * dev-<requirements>.<ext>
        # * <requirements>_dev.<ext>
        # * dev_<requirements>.<ext>
        # * <requirements>dev.<ext>
        # * dev<requirements>.<ext>
        #
        # Where <requirements> is basename of given requirements file to use
        # and <ext> is its extension.
        for delimiter in ('-', '_', ''):
            filename = os.path.join(
                dirname, ''.join((basename, delimiter, 'dev', ext))
            )
            if os.path.isfile(filename):
                dev_requirements = filename
                break

            filename = os.path.join(
                dirname, ''.join(('dev', delimiter, basename, ext))
            )
            if os.path.isfile(filename):
                dev_requirements = filename
                break

        # If at least one dev requirements file found, install dev requirements
        if dev_requirements:
            if not quiet:
                print('== Install dev requirements ==')

            pip_cmd(env,
                    ('install', '-r', dev_requirements),
                    ignore_activated,
                    echo=not quiet)

            if not quiet:
                print()

    return result


def iteritems(data, **kwargs):
    """Iterate over dict items."""
    return iter(data.items(**kwargs)) if IS_PY3 else data.iteritems(**kwargs)


def iterkeys(data, **kwargs):
    """Iterate over dict keys."""
    return iter(data.keys(**kwargs)) if IS_PY3 else data.iterkeys(**kwargs)


@error_handler
def main(*args):
    r"""Bootstrap Python projects and libraries with virtualenv and pip.

    Also check system requirements before bootstrap and run post bootstrap
    hook if any.

    :param \*args: Command line arguments list.
    """
    # Create parser, read arguments from direct input or command line
    with disable_error_handler():
        args = parse_args(args or sys.argv[1:])

    # Read current config from file and command line arguments
    config = read_config(args.config, args)
    if config is None:
        return True
    bootstrap = config[__script__]

    # Check pre-requirements
    if not check_pre_requirements(bootstrap['pre_requirements']):
        return True

    # Create virtual environment
    env_args = prepare_args(config['virtualenv'], bootstrap)
    if not create_env(
        bootstrap['env'],
        env_args,
        bootstrap['recreate'],
        bootstrap['ignore_activated'],
        bootstrap['quiet']
    ):
        # Exit if couldn't create virtual environment
        return True

    # And install library or project here
    pip_args = prepare_args(config['pip'], bootstrap)
    if not install(
        bootstrap['env'],
        bootstrap['requirements'],
        pip_args,
        bootstrap['ignore_activated'],
        bootstrap['install_dev_requirements'],
        bootstrap['quiet']
    ):
        # Exist if couldn't install requirements into venv
        return True

    # Run post-bootstrap hook
    run_hook(bootstrap['hook'], bootstrap, bootstrap['quiet'])

    # All OK!
    if not bootstrap['quiet']:
        print('All OK!')

    # False means everything went alright, exit code: 0
    return False


def parse_args(args):
    """
    Parse args from command line by creating argument parser instance and
    process it.

    :param args: Command line arguments list.
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
             format(CONFIG[__script__]['requirements'])
    )
    parser.add_argument(
        '-d', '--install-dev-requirements', action='store_true', default=None,
        help='Install prefixed or suffixed "dev" requirements after '
             'installation of original requirements file completed without '
             'errors. This flag makes sense only for bootstrapping projects '
             'and would be ignored for bootstrapping libraries.'
    )
    parser.add_argument(
        '-C', '--hook', help='Execute this hook after bootstrap process.'
    )
    parser.add_argument(
        '--ignore-activated', action='store_true', default=None,
        help='Ignore pre-activated virtualenv, like on Travis CI.'
    )
    parser.add_argument(
        '--recreate', action='store_true', default=None,
        help='Recreate virtualenv on every run.'
    )
    parser.add_argument(
        '-q', '--quiet', action='store_true', default=None,
        help='Minimize output, show only error messages.'
    )

    return parser.parse_args(args)


def pip_cmd(env, cmd, ignore_activated=False, **kwargs):
    r"""Run pip command in given or activated virtual environment.

    :param env: Virtual environment name.
    :param cmd: Pip subcommand to run.
    :param ignore_activated:
        Ignore activated virtual environment and use given venv instead. By
        default: False
    :param \*\*kwargs:
        Additional keyword arguments to be passed to :func:`~run_cmd`
    """
    cmd = tuple(cmd)
    dirname = safe_path(env)

    if not ignore_activated:
        activated_env = os.environ.get('VIRTUAL_ENV')

        if hasattr(sys, 'real_prefix'):
            dirname = sys.prefix
        elif activated_env:
            dirname = activated_env

    pip_path = os.path.join(dirname, 'Scripts' if IS_WINDOWS else 'bin', 'pip')

    if kwargs.pop('return_path', False):
        return pip_path

    if not os.path.isfile(pip_path):
        raise OSError('No pip found at {0!r}'.format(pip_path))

    with disable_error_handler():
        return run_cmd((pip_path, ) + cmd, **kwargs)


def prepare_args(config, bootstrap):
    """Convert config dict to command line args line.

    :param config: Configuration dict.
    :param bootstrap: Bootstrapper configuration dict.
    """
    config = copy.deepcopy(config)
    environ = dict(copy.deepcopy(os.environ))

    data = {'env': bootstrap['env'],
            'pip': pip_cmd(bootstrap['env'], '', return_path=True),
            'requirements': bootstrap['requirements']}
    environ.update(data)

    if isinstance(config, string_types):
        return config.format(**environ)

    for key, value in iteritems(config):
        if not isinstance(value, string_types):
            continue
        config[key] = value.format(**environ)

    return config_to_args(config)


def print_error(message, wrap=True):
    """Print error message to stderr, using ANSI-colors.

    :param message: Message to print
    :param wrap:
        Wrap message into ``ERROR: <message>. Exit...`` template. By default:
        True
    """
    if wrap:
        message = 'ERROR: {0}. Exit...'.format(message.rstrip('.'))

    colorizer = (_color_wrap(colorama.Fore.RED)
                 if colorama
                 else lambda message: message)
    return print(colorizer(message), file=sys.stderr)


def read_config(filename, args):
    """
    Read and parse configuration file. By default, ``filename`` is relative
    path to current work directory.

    If no config file found, default ``CONFIG`` would be used.

    :param filename: Read config from given filename.
    :param args: Parsed command line arguments.
    """
    # Initial vars
    config = defaultdict(dict)
    splitter = operator.methodcaller('split', ' ')

    converters = {
        __script__: {
            'env': safe_path,
            'pre_requirements': splitter,
        },
        'pip': {
            'allow_external': splitter,
            'allow_unverified': splitter,
        }
    }
    default = copy.deepcopy(CONFIG)
    sections = set(iterkeys(default))

    # Append download-cache for old pip versions
    if int(getattr(pip, '__version__', '1.x')[0]) < 6:
        default['pip']['download_cache'] = safe_path(os.path.expanduser(
            os.path.join('~', '.{0}'.format(__script__), 'pip-cache')
        ))

    # Expand user and environ vars in config filename
    is_default = filename == DEFAULT_CONFIG
    filename = os.path.expandvars(os.path.expanduser(filename))

    # Read config if it exists on disk
    if not is_default and not os.path.isfile(filename):
        print_error('Config file does not exist at {0!r}'.format(filename))
        return None

    parser = ConfigParser()

    try:
        parser.read(filename)
    except ConfigParserError:
        print_error('Cannot parse config file at {0!r}'.format(filename))
        return None

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
        'env', 'hook', 'install_dev_requirements', 'ignore_activated',
        'pre_requirements', 'quiet', 'recreate', 'requirements'
    ))

    for key in keys:
        value = getattr(args, key)
        config[__script__].setdefault(key, value)

        if key == 'pre_requirements' and not value:
            continue

        if value is not None:
            config[__script__][key] = value

    return config


def run_cmd(cmd, echo=False, fail_silently=False, **kwargs):
    r"""Call given command with ``subprocess.call`` function.

    :param cmd: Command to run.
    :type cmd: tuple or str
    :param echo:
        If enabled show command to call and its output in STDOUT, otherwise
        hide all output. By default: False
    :param fail_silently: Do not raise exception on error. By default: False
    :param \*\*kwargs:
        Additional keyword arguments to be passed to ``subprocess.call``
        function. STDOUT and STDERR streams would be setup inside of function
        to ensure hiding command output in case of disabling ``echo``.
    """
    out, err = None, None

    if echo:
        cmd_str = cmd if isinstance(cmd, string_types) else ' '.join(cmd)
        kwargs['stdout'], kwargs['stderr'] = sys.stdout, sys.stderr
        print('$ {0}'.format(cmd_str))
    else:
        out, err = get_temp_streams()
        kwargs['stdout'], kwargs['stderr'] = out, err

    try:
        retcode = subprocess.call(cmd, **kwargs)
    except subprocess.CalledProcessError as err:
        if fail_silently:
            return False
        print_error(str(err) if IS_PY3 else unicode(err))  # noqa
    finally:
        if out:
            out.close()
        if err:
            err.close()

    if retcode and echo and not fail_silently:
        print_error('Command {0!r} returned non-zero exit status {1}'.
                    format(cmd_str, retcode))

    return retcode


def run_hook(hook, config, quiet=False):
    """Run post-bootstrap hook if any.

    :param hook: Hook to run.
    :param config: Configuration dict.
    :param quiet: Do not output messages to STDOUT/STDERR. By default: False
    """
    if not hook:
        return True

    if not quiet:
        print('== Step 3. Run post-bootstrap hook ==')

    result = not run_cmd(prepare_args(hook, config),
                         echo=not quiet,
                         fail_silently=True,
                         shell=True)

    if not quiet:
        print()

    return result


def safe_path(path):
    """Replace slashes for Windows pathes.

    :param path: OS-independent path value.
    """
    return path.replace('/', os.sep) if IS_WINDOWS else path


def save_traceback(err):
    """Save error traceback to bootstrapper log file.

    :param err: Catched exception.
    """
    # Store logs to ~/.bootstrapper directory
    dirname = safe_path(os.path.expanduser(
        os.path.join('~', '.{0}'.format(__script__))
    ))

    # But ensure that directory exists
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    # Now we ready to put traceback to log file
    filename = os.path.join(dirname, '{0}.log'.format(__script__))

    with open(filename, 'a+') as handler:
        traceback.print_exc(file=handler)

    # And show colorized message
    message = ('User aborted workflow'
               if isinstance(err, KeyboardInterrupt)
               else 'Unexpected error catched')
    print_error(message)
    print_error('Full log stored to {0}'.format(filename), False)

    return True


def smart_str(value, encoding='utf-8', errors='strict'):
    """Convert Python object to string.

    :param value: Python object to convert.
    :param encoding: Encoding to use if in Python 2 given object is unicode.
    :param errors: Errors mode to use if in Python 2 given object is unicode.
    """
    if not IS_PY3 and isinstance(value, unicode):  # noqa
        return value.encode(encoding, errors)
    return str(value)


def which(executable):
    """Shortcut to check whether executable available in current env or not.

    :param executable: Executable to check.
    """
    cmd = 'where' if IS_WINDOWS else 'which'
    return not run_cmd((cmd, executable), fail_silently=True)


if __name__ == '__main__':
    sys.exit(int(main()))
