import glob
import json
import textwrap
from StringIO import StringIO
from unittest import TestCase

import os
from elasticgit.tests.base import TestPerson
from elasticgit.commands.avro import serialize
from pyramid import testing
from git import Repo

from unicore.distribute.tests.base import DistributeTestCase
from unicore.distribute.utils import (
    UCConfigParser, get_repositories, get_repository, format_repo,
    format_content_type, format_content_type_object, list_schemas, get_schema,
    get_repository_diff, pull_repository_files, add_model_item_to_pull_dict,
    clone_repository, list_content_types)


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


class TestRepositoryUtils(DistributeTestCase):
    maxDiff = None
    initial_commit = ""

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
        self.workspace.repo.index.commit('Initial commit')
        formatted = format_repo(self.workspace.repo)
        self.assertEqual(
            set(formatted.keys()),
            set(['name',
                 'commit',
                 'timestamp',
                 'author',
                 'schemas',
                 'branch']))
        last_commit = self.workspace.repo.commit()
        self.assertEqual(formatted['commit'], last_commit.hexsha)
        self.assertEqual(
            formatted['author'], '%s <%s>' % (last_commit.author.name,
                                              last_commit.author.email))

    def test_format_content_type(self):
        p = TestPerson({'name': 'Foo', 'age': 1})
        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.save(p, 'Saving a person.')
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        [model_obj] = format_content_type(
            self.workspace.repo, '%(namespace)s.%(name)s' % schema)
        self.assertEqual(TestPerson(model_obj), p)

    def test_format_content_type_object(self):
        p = TestPerson({'name': 'Foo', 'age': 1})
        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        self.workspace.save(p, 'Saving a person.')
        model_obj = format_content_type_object(
            self.workspace.repo, '%(namespace)s.%(name)s' % schema,
            p.uuid)
        self.assertEqual(TestPerson(model_obj), p)

    def test_list_schemas(self):
        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        schemas = list_schemas(self.workspace.repo)
        found_schema = schemas['%(namespace)s.%(name)s' % schema]
        self.assertEqual(found_schema['namespace'], schema['namespace'])
        self.assertEqual(found_schema['name'], schema['name'])

    def test_list_content_types(self):
        self.add_schema(self.workspace, TestPerson)
        content_types = list_content_types(self.workspace.repo)
        self.assertEqual(content_types, ['elasticgit.tests.base.TestPerson'])

    def test_get_schema(self):
        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        found_schema = get_schema(
            self.workspace.repo,
            '%(namespace)s.%(name)s' % schema).to_json()
        self.assertEqual(found_schema['namespace'], schema['namespace'])
        self.assertEqual(found_schema['name'], schema['name'])


class TestRepositoryUtils2(DistributeTestCase):
    """
    Separate class because initialising repo on setup above breaks other tests
    """

    initial_commit = ""
    schema_names = []

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.add_schema(self.workspace, TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })
        person1 = TestPerson({'age': 12, 'name': 'Foo'})
        person2 = TestPerson({'age': 34, 'name': 'Bar'})
        self.create_commit("initial commit")
        self.workspace.save(person1, "saving person 1")
        self.workspace.save(person2, "saving person 2")
        self.create_commit("second commit")
        self.schema_names = set(self.create_schema_names())

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

    def create_schema_names(self):
        schema_files = glob.glob(os.path.join(self.workspace.repo.working_dir,
                                              '_schemas', '*.avsc'))
        names = []
        for schema_file in schema_files:
            names.append(os.path.basename(os.path.splitext(schema_file)[0]))
        return names

    def create_commit(self, message):
        repo = Repo(self.workspace.working_dir)
        repo.commit(repo.index.commit(message))
        return repo.commit().hexsha

    def test_add_model_item_to_pull_dict(self):
        person = TestPerson({'age': 22, 'name': 'testing'})
        self.workspace.save(person, 'saving person testing')
        path = self.workspace.sm.git_name(person)
        response = {TestPerson.__module__ + '.' + TestPerson.__name__: []}
        added = add_model_item_to_pull_dict(self.workspace.sm, path, response)
        self.assertTrue(added)

    def test_get_repository_diff(self):
        diff = get_repository_diff(self.workspace.repo, self.initial_commit)
        self.assertEqual(set(diff.keys()),
                         {'current-index', 'previous-index', 'name', 'diff'})
        self.assertEqual(diff['current-index'],
                         self.workspace.repo.head.commit.hexsha)
        self.assertEqual(diff['previous-index'],
                         self.initial_commit)
        self.assertEqual(diff['name'],
                         os.path.basename(self.workspace.repo.working_dir))

    def test_pull_repository_files(self):
        pull = pull_repository_files(self.workspace.repo, self.initial_commit)
        self.assertEqual(set(pull.keys()),
                         {'commit', 'other'} | self.schema_names)
        self.assertEqual(pull['commit'],
                         self.workspace.repo.head.commit.hexsha)

    def test_clone_repository(self):
        clone = clone_repository(self.workspace.repo)
        self.assertEqual(set(clone), {'commit'} | self.schema_names)
        self.assertEqual(clone['commit'],
                         self.workspace.repo.head.commit.hexsha)
