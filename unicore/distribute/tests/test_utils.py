import textwrap

from StringIO import StringIO
from unittest import TestCase

from unicore.distribute.utils import (
    UCConfigParser, get_repositories, get_repository, format_repo)

from elasticgit.tests.base import ModelBaseTest

from git import Repo


class TestUCConfigParser(TestCase):

    def setUp(self):
        sio = StringIO(textwrap.dedent("""
            [foo]
            list =
                1
                2
                3

            dict =
                a = 1
                b = 2
                c = 3
            """))
        self.cp = UCConfigParser()
        self.cp.readfp(sio)

    def test_get_list(self):
        self.assertEqual(self.cp.get_list('foo', 'list'), ['1', '2', '3'])

    def test_get_dict(self):
        self.assertEqual(self.cp.get_dict('foo', 'dict'), {
            'a': '1',
            'b': '2',
            'c': '3',
        })


class TestRepositoryUtils(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_get_repositories(self):
        [repo] = get_repositories(self.WORKING_DIR)
        self.assertTrue(isinstance(repo, Repo))
        self.assertEqual(repo.working_dir, self.workspace.working_dir)

    def test_get_repository(self):
        repo = get_repository(self.workspace.working_dir)
        self.assertTrue(isinstance(repo, Repo))
        self.assertEqual(repo.working_dir, self.workspace.working_dir)

    def test_format_repo(self):
        formatted = format_repo(self.workspace.repo)
        self.assertEqual(
            set(formatted.keys()),
            set(['name', 'commit', 'timestamp', 'author', 'schemas']))
        last_commit = self.workspace.repo.commit()
        self.assertEqual(formatted['commit'], last_commit.hexsha)
        self.assertEqual(
            formatted['author'], '%s <%s>' % (last_commit.author.name,
                                              last_commit.author.email))
