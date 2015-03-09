import os
import json

from elasticgit.commands.avro import serialize
from elasticgit.tests.base import TestPerson, ModelBaseTest
from elasticgit.utils import fqcn

from cornice.errors import Errors

from unicore.distribute.api.validators import validate_schema

from pyramid import testing


class TestValidators(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

        self.person = TestPerson({'name': 'Foo', 'age': 1})
        self.request = testing.DummyRequest()
        self.request.errors = Errors()
        self.config = testing.setUp(
            settings={
                'repo.storage_path': self.WORKING_DIR,
            }, request=self.request)

    def test_validate_schema_valid(self):
        self.request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        self.request.body = json.dumps(dict(self.person))
        validate_schema(self.request)
        self.assertEqual(self.request.errors, [])

    def test_validate_schema_invalid(self):
        self.request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        self.request.body = json.dumps({'age': 'twenty two'})
        validate_schema(self.request)
        self.assertEqual(
            self.request.errors, [{
                'location': 'body',
                'name': 'schema',
                'description': (
                    'Data does not match the schema for '
                    'elasticgit.tests.base.TestPerson')
            }])

    def test_validate_schema_invalid_uuid(self):
        self.request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': 'foo',
        }
        self.request.body = json.dumps(dict(self.person))
        validate_schema(self.request)
        self.assertEqual(
            self.request.errors, [{
                'location': 'body',
                'name': 'uuid',
                'description': 'Payload UUID does not match URL UUID.'}])
