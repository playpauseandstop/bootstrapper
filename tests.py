#!/usr/bin/env python

import os
import subprocess
import sys
import tempfile
import unittest


DIRNAME = os.path.abspath(os.path.dirname(__file__))
IS_PY3 = sys.version_info[0] == 3


class TestBootstrapper(unittest.TestCase):

    default_config = 'bootsrap.cfg'
    default_requirements = 'requirements.txt'
    default_venv = 'env'
    prefix = ''

    def tearDown(self):
        files = set([self.default_config, self.default_requirements,
                     self.default_venv, self.config, self.requirements,
                     self.venv])
        self.run_cmd('rm -rf {0}'.format(' '.join(files)))

    @property
    def config(self):
        return getattr(self, '_config', self.default_config)

    @config.setter
    def config(self, value):
        setattr(self, '_config', value)

    def init_config(self, **content):
        pass

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

    @property
    def requirements(self):
        if self.prefix:
            return 'requirements-{0}.txt'.format(self.prefix)
        return self.default_requirements

    def run_cmd(self, cmd=None):
        tout, terr = tempfile.TemporaryFile(), tempfile.TemporaryFile()

        cmd = cmd or './bootstrapper.py'
        kwargs = {'shell': True, 'stdout': tout, 'stderr': terr}
        subprocess.call('cd {0} && {1}'.format(DIRNAME, cmd), **kwargs)

        tout.seek(0)
        out = tout.read()
        tout.close()

        terr.seek(0)
        err = terr.read()
        terr.close()

        if IS_PY3:
            out, err = str(out), str(err)

        return out, err

    @property
    def venv(self):
        if self.prefix:
            return '{0}-{1}'.format(self.default_venv, self.prefix)
        return self.default_venv

    def test_normal_case(self):
        self.init_requirements('ordereddict==1.1')
        out, err = self.run_cmd()
        self.assertTrue(os.path.isdir(self.venv), self.message(out, err))

        out, err = self.run_cmd('{0}/bin/pip freeze'.format(self.venv))
        self.assertIn('ordereddict==1.1', out)

    def test_special_case(self):
        self.assertEqual(self.requirements, self.default_requirements)
        self.assertEqual(self.venv, self.default_venv)

        self.init_requirements('ordereddict==1.1', 'MiniMock==1.2.7')
        out, err = self.run_cmd()
        self.assertTrue(os.path.isdir(self.venv), self.message(out, err))

        self.prefix = 'trunk'
        self.assertNotEqual(self.requirements, self.default_requirements)
        self.assertNotEqual(self.venv, self.default_venv)

        self.init_requirements('ordereddict==1.1', 'MiniMock==1.2.5')
        out, err = self.run_cmd()
        self.assertTrue(os.path.isdir(self.venv), self.message(out, err))

        out, err = self.run_cmd('{0}/bin/pip freeze'.format(self.venv))
        self.assertIn('MiniMock==1.2.5', out)


if __name__ == '__main__':
    unittest.main()
