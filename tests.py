#!/usr/bin/env python

from __future__ import absolute_import

import os
import shlex
import shutil
import sys
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from contextlib import contextmanager
from random import choice, randint

import pip

import bootstrapper


DIRNAME = os.path.abspath(os.path.dirname(__file__))
TEST_CONFIG = """[bootstrapper]
pre_requirements = python
quiet = True

[pip]
allow_external = elementtree PIL polib
allow_unverified = elementtree PIL polib
"""


class TestBootstrapper(unittest.TestCase):

    config = None
    requirements = 'test-requirements.txt'
    venv = 'test-env'

    def setUp(self):
        os.environ[bootstrapper.BOOTSTRAPPER_TEST_KEY] = '1'

    def tearDown(self):
        if bootstrapper.BOOTSTRAPPER_TEST_KEY in os.environ:
            os.environ.pop(bootstrapper.BOOTSTRAPPER_TEST_KEY)

        if self.config is not None:
            self.delete(self.config)

        self.delete(self.requirements,
                    self.dev_requirements,
                    bootstrapper.safe_path(self.venv))

    def delete(self, *files):
        for item in files:
            if os.path.isfile(item):
                os.unlink(item)
            elif os.path.isdir(item):
                shutil.rmtree(item)

    @property
    def dev_requirements(self):
        if not hasattr(self, '_dev_requirements'):
            delimiter = choice(('-', '_', ''))
            prefixed = randint(0, 1)

            basename, ext = os.path.splitext(self.requirements)
            parts = ((basename, delimiter, 'dev', ext)
                     if prefixed
                     else ('dev', delimiter, basename, ext))
            setattr(self, '_dev_requirements', ''.join(parts))

        return getattr(self, '_dev_requirements')

    def init_requirements(self, *lines, **kwargs):
        filename = kwargs.pop('filename', None) or self.requirements
        with open(filename, 'w+') as handler:
            handler.write('\n'.join(lines))
        self.assertTrue(os.path.isfile(filename))

    def message(self, out, err, echo=False):
        output = '\n'.join(('[STDOUT]', out, '', '[STDERR]', err))
        if echo:
            print(output)
        else:
            return output

    @contextmanager
    def redirect_streams(self, out, err):
        original_out, original_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        yield
        sys.stdout, sys.stderr = original_out, original_err

        out.seek(0)
        err.seek(0)

    def run_cmd(self, cmd):
        kwargs = {}
        inside_tox = 'BOOTSTRAPPER_TOX' in os.environ
        out, err = bootstrapper.get_temp_streams()

        if cmd.startswith('bootstrap'):
            func = bootstrapper.main
            args = tuple(shlex.split(cmd)[1:])
            args += ('-e', self.venv, '-r', self.requirements)
            if self.config:
                args += ('-c', self.config)
            if inside_tox:
                args += ('--ignore-activated', )
        elif cmd.startswith('pip '):
            func = bootstrapper.pip_cmd
            args = (self.venv, cmd[4:].split(), inside_tox, )
            kwargs['echo'] = True
        else:
            assert False, 'Command {0!r} is not supported!'.format(cmd)

        with self.redirect_streams(out, err):
            func(*args, **kwargs)

        try:
            return (out.read(), err.read())
        finally:
            out.close()
            err.close()

    def test_install_dev_requirements_library(self):
        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('MiniMock==1.2.8',
                               filename=self.dev_requirements)

        out, err = self.run_cmd('bootstrap -d')
        base_debug = self.message(out, err)
        self.assertTrue(os.path.isdir(self.venv), base_debug)

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((base_debug, self.message(pip_out, pip_err)))
        self.assertIn('playpauseandstop/bootstrapper.git@', pip_out, debug)
        self.assertIn('MiniMock==1.2.8', pip_out, debug)

    def test_install_dev_requirements_project(self):
        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('ordereddict==1.1')
        self.init_requirements('MiniMock==1.2.8',
                               filename=self.dev_requirements)

        out, err = self.run_cmd('bootstrap -d')
        base_debug = self.message(out, err)
        self.assertTrue(os.path.isdir(self.venv), base_debug)

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((base_debug, self.message(pip_out, pip_err)))
        self.assertIn('ordereddict==1.1', pip_out, debug)
        self.assertIn('MiniMock==1.2.8', pip_out, debug)

    def test_install_error(self):
        os.environ.pop(bootstrapper.BOOTSTRAPPER_TEST_KEY)

        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('ordereddict==1.1')

        os.mkdir(self.venv)
        out, err = self.run_cmd('bootstrap')
        debug = self.message(out, err)

        self.assertIn('ERROR: Unexpected error catched. Exit...', err, debug)
        self.assertIn('Full log stored to ', err, debug)

    def test_library_bootstrap(self):
        self.assertFalse(os.path.isdir(self.venv))
        out, err = self.run_cmd('bootstrap')
        base_debug = self.message(out, err)
        self.assertTrue(os.path.isdir(self.venv), base_debug)

        if self.config:
            self.assertIn('--allow-external argparse', out, base_debug)

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((base_debug, self.message(pip_out, pip_err)))
        self.assertIn('playpauseandstop/bootstrapper.git@', pip_out, debug)
        self.assertIn('#egg=bootstrapper', pip_out, debug)

    def test_no_config_error(self):
        self.config = '/path/does-not-exist.cfg'
        self.assertFalse(os.path.isfile(self.config))

        out, err = self.run_cmd('bootstrap')
        debug = self.message(out, err)

        self.assertEqual(out, '', debug)
        self.assertIn(
            'ERROR: Config file does not exist at {0!r}. Exit...'.
            format(self.config),
            err,
            debug
        )

    def test_no_post_bootstrap_hook(self):
        self.init_requirements('does-not-exist==X.Y')
        out, err = self.run_cmd('bootstrap -C "echo Succeed..."')
        debug = self.message(out, err)
        self.assertNotIn('Succeed...', out, debug)

    def test_pip_cmd(self):
        pip_path = bootstrapper.pip_cmd(self.venv, '', True, return_path=True)
        self.assertEqual(
            pip_path,
            os.path.join(self.venv.rstrip('/'),
                         'Scripts' if bootstrapper.IS_WINDOWS else 'bin',
                         'pip')
        )

    def test_project_bootstrap(self):
        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('ordereddict==1.1')

        out, err = self.run_cmd('bootstrap')
        base_debug = self.message(out, err)
        self.assertTrue(os.path.isdir(self.venv), base_debug)

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((base_debug, self.message(pip_out, pip_err)))
        self.assertIn('ordereddict==1.1', pip_out, debug)

    def test_repeatable_bootstrap(self):
        self.init_requirements('ordereddict==1.1')
        _, err = self.run_cmd('bootstrap')
        self.assertEqual(err, '')

        _, err = self.run_cmd('bootstrap')
        self.assertEqual(err, '')


class TestBootstrapperNoDashes(TestBootstrapper):

    requirements = 'venvrequirements.txt'
    venv = 'venv/'


class TestOther(unittest.TestCase):

    config = None

    def setUp(self):
        os.environ[bootstrapper.BOOTSTRAPPER_TEST_KEY] = '1'

    def tearDown(self):
        os.environ.pop(bootstrapper.BOOTSTRAPPER_TEST_KEY)
        if self.config and os.path.isfile(self.config.name):
            os.unlink(self.config.name)

    def test_config_to_args(self):
        default_pip_config = bootstrapper.CONFIG['pip']
        config = {
            'allow_external': ['elementtree', 'PIL', 'polib'],
            'quiet': True,
            'timeout': 30,
        }
        if default_pip_config.get('download_cache'):
            config['download_cache'] = default_pip_config['download_cache']

        args = bootstrapper.config_to_args(config)

        self.assertEqual(args.count('--allow-external'), 3)
        if default_pip_config.get('download_cache'):
            self.assertEqual(args.count('--download-cache'), 1)
        self.assertIn('--quiet', args)
        self.assertIn('--timeout', args)
        self.assertIn('30', args)

        index = args.index('--timeout')
        self.assertEqual(args[index + 1], '30')

    def test_get_streams(self):
        out, err = bootstrapper.get_temp_streams()

        out.write('Output'), err.write('Error')
        out.seek(0), err.seek(0)

        self.assertEqual(out.read(), 'Output')
        self.assertEqual(err.read(), 'Error')

        out.close()
        err.close()

    def test_read_config(self):
        default_pip_config = bootstrapper.CONFIG['pip']
        expected_pip_config = {
            'allow_external': ['elementtree', 'PIL', 'polib'],
            'allow_unverified': ['elementtree', 'PIL', 'polib'],
        }
        if default_pip_config.get('download_cache'):
            expected_pip_config.update({
                'download_cache': default_pip_config['download_cache'],
            })

        kwargs = {'delete': False, 'prefix': 'bootstrap', 'suffix': '.cfg'}
        if bootstrapper.IS_PY3:
            kwargs.update({'encoding': 'utf-8'})

        self.config = tempfile.NamedTemporaryFile('w+', **kwargs)
        self.config.write(TEST_CONFIG)
        self.config.close()

        args = bootstrapper.parse_args([])
        config = bootstrapper.read_config(self.config.name, args)

        script = bootstrapper.__script__
        self.assertEqual(config[script]['pre_requirements'], ['python'])
        self.assertTrue(config[script]['quiet'])
        self.assertEqual(config['pip'], expected_pip_config)
        self.assertEqual(config['virtualenv'], {})

    def test_which(self):
        self.assertTrue(bootstrapper.which('python'))
        self.assertFalse(bootstrapper.which('does-not-exist'))


if __name__ == '__main__':
    unittest.main()
