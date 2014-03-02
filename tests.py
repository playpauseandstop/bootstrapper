#!/usr/bin/env python

from __future__ import absolute_import

import os
import shutil
import sys
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from contextlib import contextmanager

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
        self.delete(self.requirements, bootstrapper.safe_path(self.venv))

    def delete(self, *files):
        for item in files:
            if os.path.isfile(item):
                os.unlink(item)
            elif os.path.isdir(item):
                shutil.rmtree(item)

    def init_requirements(self, *lines):
        with open(self.requirements, 'w+') as handler:
            handler.write('\n'.join(lines))
        self.assertTrue(os.path.isfile(self.requirements))

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
        on_travis = 'TRAVIS_PYTHON_VERSION' in os.environ
        out, err = bootstrapper.get_temp_streams()

        if cmd == 'bootstrap':
            func = bootstrapper.main
            args = ('-e', self.venv, '-r', self.requirements)
            if self.config:
                args += ('-c', self.config)
            if on_travis:
                args += ('--ignore-activated', )
        elif cmd.startswith('pip '):
            func = bootstrapper.pip_cmd
            args = (self.venv, cmd[4:].split(), on_travis, )
            kwargs['echo'] = True
        else:
            assert False, 'Command {0!r} is not supported!'.format(cmd)

        with self.redirect_streams(out, err):
            func(*args, **kwargs)

        return (out.read(), err.read())

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
        # We need to allow install argparse from external
        pip_version_info = map(int, pip.__version__.split('.'))[:2]
        if sys.version_info[:2] < (2, 7) and pip_version_info >= (1, 5):
            self.config = '{0}.cfg'.format(self.venv)
            with open(self.config, 'w+') as handler:
                handler.write('[pip]\nallow_external = argparse\n')

        self.assertFalse(os.path.isdir(self.venv))
        out, err = self.run_cmd('bootstrap')
        self.assertTrue(os.path.isdir(self.venv))

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((self.message(out, err),
                           self.message(pip_out, pip_err)))
        self.assertIn('playpauseandstop/bootstrapper.git@', pip_out, debug)
        self.assertIn('#egg=bootstrapper-', pip_out, debug)

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
        self.assertTrue(os.path.isdir(self.venv), self.message(out, err))

        pip_out, pip_err = self.run_cmd('pip freeze')
        debug = '\n'.join((self.message(out, err),
                           self.message(pip_out, pip_err)))
        self.assertIn('ordereddict==1.1', pip_out, debug)


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
        config = {
            'allow_external': ['elementtree', 'PIL', 'polib'],
            'download_cache': bootstrapper.CONFIG['pip']['download_cache'],
            'quiet': True,
            'timeout': 30,
        }
        args = bootstrapper.config_to_args(config)

        self.assertEqual(args.count('--allow-external'), 3)
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

    def test_read_config(self):
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
        self.assertEqual(
            config['pip'],
            {
                'allow_external': ['elementtree', 'PIL', 'polib'],
                'allow_unverified': ['elementtree', 'PIL', 'polib'],
                'download_cache': bootstrapper.CONFIG['pip']['download_cache'],
            }
        )
        self.assertEqual(config['virtualenv'], {})

    def test_which(self):
        self.assertTrue(bootstrapper.which('python'))
        self.assertFalse(bootstrapper.which('does-not-exist'))


if __name__ == '__main__':
    unittest.main()
