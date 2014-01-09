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

    requirements = 'test-requirements.txt'
    venv = 'test-env'

    def setUp(self):
        os.environ[bootstrapper.BOOTSTRAPPER_TEST_KEY] = '1'
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def tearDown(self):
        if bootstrapper.BOOTSTRAPPER_TEST_KEY in os.environ:
            os.environ.pop(bootstrapper.BOOTSTRAPPER_TEST_KEY)
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
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

    def run_cmd(self, cmd):
        kwargs = {'encoding': 'utf-8'} if bootstrapper.IS_PY3 else {}
        tout = tempfile.TemporaryFile('w+', **kwargs)
        terr = tempfile.TemporaryFile('w+', **kwargs)
        sys.stdout, sys.stderr = tout, terr

        if cmd == 'bootstrap':
            bootstrapper.main('-e', self.venv, '-r', self.requirements)
        elif cmd.startswith('pip '):
            bootstrapper.pip_cmd(self.venv, cmd[4:].split(), echo=True)
        else:
            assert False, 'Command {0!r} is not supported!'.format(cmd)

        tout.seek(0)
        terr.seek(0)

        return (tout.read(), terr.read())

    def test_application_bootstrap(self):
        self.assertFalse(os.path.isdir(self.venv))
        out, err = self.run_cmd('bootstrap')
        self.assertTrue(os.path.isdir(self.venv))

        out, _ = self.run_cmd('pip freeze')
        self.assertIn('playpauseandstop/bootstrapper.git@', out)
        self.assertIn('#egg=bootstrapper-', out)

    def test_install_error(self):
        os.environ.pop(bootstrapper.BOOTSTRAPPER_TEST_KEY)

        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('ordereddict==1.1')

        os.mkdir(self.venv)
        out, err = self.run_cmd('bootstrap')

        self.assertIn('ERROR: Unexpected error catched. Exit...', err)
        self.assertIn('Full log stored to ', err)

    def test_pip_cmd(self):
        pip_path = bootstrapper.pip_cmd(self.venv, '', return_path=True)
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

        out, _ = self.run_cmd('pip freeze')
        self.assertIn('ordereddict==1.1', out)


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


if __name__ == '__main__':
    unittest.main()
