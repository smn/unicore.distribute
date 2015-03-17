from __future__ import absolute_import

import json
import os

from cornice.errors import Errors

from elasticgit import EG
from elasticgit.tests.base import TestPerson, ModelBaseTest
from elasticgit.commands.avro import serialize
from elasticgit.utils import fqcn

from pyramid import testing
from pyramid.exceptions import NotFound

import avro

from unicore.distribute.api.repos import (
    RepositoryResource, ContentTypeResource)
from unicore.distribute.utils import (
    format_repo, format_content_type, format_content_type_object)


class TestRepositoryResource(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        schema_string = serialize(TestPerson)
        schema = json.loads(schema_string)
        self.workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })

    def test_collection_get(self):
        request = testing.DummyRequest({})
        resource = RepositoryResource(request)
        [repo_json] = resource.collection_get()
        self.assertEqual(repo_json, format_repo(self.workspace.repo))

    def test_collection_post_success(self):
        # NOTE: cloning to a different directory called `remote` because
        #       the API is trying to clone into the same folder as the
        #       tests: self.WORKING_DIR.
        #
        # FIXME: This is too error prone & tricky to reason about
        api_repo_name = '%s_remote' % (self.id(),)
        self.remote_workspace = self.mk_workspace(
            working_dir=os.path.join(self.WORKING_DIR, 'remote'),
            name=api_repo_name)
        request = testing.DummyRequest({})
        request.validated = {
            'repo_url': self.remote_workspace.working_dir,
        }
        # Cleanup the repo created by the API on tear down
        self.addCleanup(
            lambda: EG.workspace(
                os.path.join(
                    self.WORKING_DIR, api_repo_name)).destroy())
        request.route_url = lambda route, name: (
            '/repos/%s.json' % (api_repo_name,))
        request.errors = Errors()
        resource = RepositoryResource(request)
        resource.collection_post()
        self.assertEqual(
            request.response.headers['Location'],
            '/repos/%s.json' % (api_repo_name,))
        self.assertEqual(request.response.status_code, 301)

    def test_collection_post_error(self):
        request = testing.DummyRequest({})
        request.validated = {
            'repo_url': 'git://example.org/bar.git',
        }
        request.errors = Errors()
        resource = RepositoryResource(request)
        resource.collection_post()
        [error] = request.errors
        self.assertEqual(error['location'], 'body')
        self.assertEqual(error['name'], 'repo_url')
        self.assertTrue(error['description'])

    def test_get(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
        }
        resource = RepositoryResource(request)
        repo_json = resource.get()
        self.assertEqual(repo_json, format_repo(self.workspace.repo))

    def test_get_404(self):
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': 'does-not-exist',
        }
        resource = RepositoryResource(request)
        self.assertRaises(NotFound, resource.get)


class TestContentTypeResource(ModelBaseTest):

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
        self.workspace.save(self.person, 'Saving a person.')
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })

    def test_collection(self):
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
        }
        resource = ContentTypeResource(request)
        content_type_json = resource.collection_get()
        self.assertEqual(
            content_type_json, format_content_type(self.workspace.repo,
                                                   fqcn(TestPerson)))

    def test_get(self):
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        resource = ContentTypeResource(request)
        object_json = resource.get()
        self.assertEqual(
            object_json, format_content_type_object(self.workspace.repo,
                                                    fqcn(TestPerson),
                                                    self.person.uuid))

    def test_get_404(self):
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': 'does not exist',
        }
        resource = ContentTypeResource(request)
        self.assertRaises(NotFound, resource.get)

    def test_put(self):
        request = testing.DummyRequest()
        request.schema = avro.schema.parse(serialize(TestPerson)).to_json()
        request.schema_data = dict(self.person)
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        request.registry = self.config.registry
        resource = ContentTypeResource(request)
        object_data = resource.put()
        self.assertEqual(TestPerson(object_data), self.person)

    def test_delete(self):
        request = testing.DummyRequest()
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        resource = ContentTypeResource(request)
        object_data = resource.delete()
        self.assertEqual(TestPerson(object_data), self.person)

        request = testing.DummyRequest({})
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        resource = ContentTypeResource(request)
        self.assertRaises(NotFound, resource.get)
