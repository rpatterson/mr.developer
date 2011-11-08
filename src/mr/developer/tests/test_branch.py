import os
import re
import subprocess
import contextlib
import unittest

from zc.buildout import testing

from mr.developer import develop


@contextlib.contextmanager
def chdir(*path):
    cwd = os.getcwd()
    if path:
        path = os.path.join(*path)
        os.chdir(path)
    yield path
    if path:
        os.chdir(cwd)


class FakeAtExit(object):

    def register(self, func, *args, **kw):
        pass
    

class TestBranch(object):

    buildout_template = """\
[sources]
pkg.foo = %(kind)s file://%(repo)s
"""

    def setUp(self):
        self.globs = self.__dict__
        testing.buildoutSetUp(self)

        self.repo = self.createRepo()
        with chdir(self.repo):
            self.write('foo.txt', 'foo contents')
            self.runCommand('add', 'foo.txt')
            self.runCommand('commit', '-m', 'Add foo file')

            with self.createBranch('bar-existing-feature'):
                self.write('foo.txt', 'bar existing feature branch contents')
                self.runCommand(
                    'commit', '-m',
                    'Modify foo file contents on existing feature branch')

        self.write('.mr.developer.cfg', "")
        self.kind = self.kind
        self.write('buildout.cfg', self.buildout_template % self.__dict__)

        self.orig_atexit = develop.atexit
        develop.atexit = FakeAtExit()
        self.develop = develop.Develop()
            
        
    def tearDown(self):
        develop.atexit = self.orig_atexit
        testing.buildoutTearDown(self)

    def runCommand(self, command, *args):
        cmd = (getattr(self, 'binary', self.kind), command
               )+self.command_args.get(command, ())+args
        return subprocess.check_output(
            cmd, stderr=subprocess.STDOUT)

    def currentBranch(self, *path):
        with chdir(*path):
            branch_out = self.runCommand('branch')
        return re.match(r'^\* (.*)$', branch_out).group(1)

    @contextlib.contextmanager
    def createBranch(self, name):
        orig = self.currentBranch()
        self.runCommand('checkout', '-b', name)
        yield name
        self.runCommand('checkout', orig)

    def createRepo(self, name='foo-repo'):
        repo_dir = self.tmpdir(name)
        with chdir(repo_dir) as repo_dir:
            self.runCommand('init')
        return repo_dir

    def read(self, *path):
        path = os.path.join(*path)
        with open(path) as file_:
            return file_.read()

    def test_branchLifeCycle(self):
        """Test the whole branch lifecycle:

        - start out on default branch
        - make a change
        - start two new branches with different changes
        - test switching between the default branch and another branch
        - test switching between two branches
        """
        self.develop('checkout', 'pkg.foo')
        self.assertEqual(
            self.read('src', 'pkg.foo', 'foo.txt'), 'foo contents')
        self.assertEqual(self.currentBranch('src', 'pkg.foo'), 'master')
            

class TestGitBranch(TestBranch, unittest.TestCase):

    kind = 'git'

    command_args = {'commit': ('-a',)}
