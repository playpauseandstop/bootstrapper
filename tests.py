#!/usr/bin/env python

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


class TestBootstrapper(unittest.TestCase):

    requirements = 'test-requirements.txt'
    venv = 'test-env'

    def tearDown(self):
        if hasattr(self, 'old_stdout'):
            sys.stdout = self.old_stdout

        if hasattr(self, 'old_stderr'):
            sys.stderr = self.old_stderr

        self.delete(self.requirements, self.venv)

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
        tout = tempfile.TemporaryFile(**kwargs)
        terr = tempfile.TemporaryFile(**kwargs)

        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = tout, terr

        if cmd == 'bootstrap':
            bootstrapper.main('-e', self.venv, '-r', self.requirements)
        elif cmd.startswith('pip '):
            bootstrapper.pip_cmd(self.venv, cmd[4:], echo=True)
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

    def test_project_bootstrap(self):
        self.assertFalse(os.path.isdir(self.venv))
        self.init_requirements('ordereddict==1.1')
        out, err = self.run_cmd('bootstrap')
        self.assertTrue(os.path.isdir(self.venv), self.message(out, err))

        out, _ = self.run_cmd('pip freeze')
        self.assertIn('ordereddict==1.1', out)


if __name__ == '__main__':
    unittest.main()
