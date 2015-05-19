import json
import os
import textwrap

from StringIO import StringIO
from unittest import TestCase

from elasticgit.tests.base import TestPerson, ModelBaseTest
from elasticgit.commands.avro import serialize

from unicore.distribute.utils import (
    UCConfigParser, get_repositories, get_repository, format_repo,
    format_content_type, format_content_type_object,
    list_schemas, get_schema)


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

    maxDiff = None

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
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        self.workspace.save(p, 'Saving a person.')
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
