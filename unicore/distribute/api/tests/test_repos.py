from __future__ import absolute_import

import json
import os

from cornice.errors import Errors

from elasticsearch import ElasticsearchException
from elasticgit import EG
from elasticgit.storage import StorageManager
from elasticgit.search import ESManager
from elasticgit.tests.base import TestPerson
from elasticgit.commands.avro import serialize
from elasticgit.utils import fqcn
from elasticgit.workspace import Workspace

from git.exc import GitCommandError

from pyramid import testing
from pyramid.exceptions import NotFound

from mock import patch, DEFAULT
import avro

from unicore.distribute.api.repos import (
    RepositoryResource, ContentTypeResource, initialize_repo_index,
    update_repo_index, index_content_type_object)
from unicore.distribute.events import (
    RepositoryCloned, RepositoryUpdated, ContentTypeObjectUpdated)
from unicore.distribute.utils import (
    format_repo, format_content_type, format_content_type_object)
from unicore.distribute.tests.base import DistributeTestCase


class TestRepositoryResource(DistributeTestCase):

    def setUp(self):
        self.workspace = self.mk_model_workspace(TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
            'es.indexing_enabled': 'true'
        })
        self.config.include('unicore.distribute.api')

    def create_upstream_for(self, workspace, create_remote=True,
                            remote_name='origin',
                            suffix='upstream'):
        upstream_workspace = self.mk_workspace(
            name='%s_%s' % (self.id().lower(), suffix),
            index_prefix='%s_%s' % (self.workspace.index_prefix,
                                    suffix))
        if create_remote:
            workspace.repo.create_remote(
                remote_name, upstream_workspace.working_dir)
        return upstream_workspace

    def test_collection_get(self):
        request = testing.DummyRequest({})
        resource = RepositoryResource(request)
        [repo_json] = resource.collection_get()
        self.assertEqual(repo_json, format_repo(self.workspace.repo))

    def test_collection_get_name_only(self):
        request = testing.DummyRequest({'name_only': True})
        resource = RepositoryResource(request)
        [repo_json] = resource.collection_get()
        self.assertEqual(repo_json, {
            'name': 'unicore.distribute.api.tests.test_repos.'
                    'TestRepositoryResource.test_collection_get_name_only'})

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
            'repo_name': None
        }
        # Cleanup the repo created by the API on tear down
        self.addCleanup(
            lambda: EG.workspace(
                os.path.join(
                    self.WORKING_DIR, api_repo_name)).destroy())
        self.addCleanup(
            lambda: EG.workspace(
                os.path.join(
                    self.WORKING_DIR, 'foo-bar')).destroy())
        request.route_url = lambda route, name: (
            '/repos/%s.json' % (api_repo_name,))
        request.errors = Errors()
        resource = RepositoryResource(request)

        with patch.object(request.registry, 'notify') as mocked_notify:
            resource.collection_post()
            self.assertEqual(
                request.response.headers['Location'],
                '/repos/%s.json' % (api_repo_name,))
            self.assertEqual(request.response.status_code, 301)
            mocked_notify.assert_called()
            (event,) = mocked_notify.call_args[0]
            self.assertIsInstance(event, RepositoryCloned)
            self.assertIs(event.config, self.config.registry.settings)
            self.assertEqual(
                event.repo.working_dir,
                os.path.abspath(os.path.join(self.WORKING_DIR, api_repo_name)))
            # check that the repo can be cloned with a different name
            request.validated['repo_name'] = 'foo-bar'
            resource.collection_post()
            self.assertEqual(request.response.status_code, 301)
            self.assertTrue(
                os.path.exists(os.path.join(self.WORKING_DIR, 'foo-bar')))

    def test_initialize_repo_index(self):
        im = self.workspace.im
        sm = self.workspace.sm
        sm.store(TestPerson({'name': 'foo'}), 'storing person')
        event = RepositoryCloned(
            repo=self.workspace.repo,
            config=self.config.registry.settings)

        with patch.object(
                ESManager, 'destroy_index', wraps=im.destroy_index
        ) as mocked_destroy:
            initialize_repo_index(event)
            self.assertTrue(mocked_destroy.called)
            self.assertTrue(im.index_exists(sm.active_branch()))
            self.assertEqual(
                im.get_mapping(sm.active_branch(), TestPerson),
                im.get_mapping_type(TestPerson).get_mapping())
            self.workspace.refresh_index()
            self.assertEqual(
                len(self.workspace.S(TestPerson).filter(name='foo')), 1)

    @patch.object(
        ESManager, 'setup_custom_mapping', side_effect=ElasticsearchException)
    def test_initialize_repo_index_error(self, mocked_setup_mapping):
        im = self.workspace.im
        sm = self.workspace.sm
        event = RepositoryCloned(
            repo=self.workspace.repo,
            config=self.config.registry.settings)

        with patch.object(
                ESManager,
                'destroy_index',
                wraps=im.destroy_index) as mocked_destroy:
            self.assertRaises(
                ElasticsearchException, initialize_repo_index, event)
            self.assertFalse(im.index_exists(sm.active_branch()))
            self.assertEqual(mocked_destroy.call_count, 2)

    @patch.object(EG, 'clone_repo')
    def test_collection_post_error(self, mock_method):
        mock_method.side_effect = GitCommandError(
            'git clone', 'Boom!', stderr='mocked response')
        request = testing.DummyRequest({})
        request.validated = {
            'repo_url': 'git://example.org/bar.git',
            'repo_name': None
        }
        request.errors = Errors()
        resource = RepositoryResource(request)
        resource.collection_post()
        [error] = request.errors
        self.assertEqual(error['location'], 'body')
        self.assertEqual(error['name'], 'repo_url')
        self.assertEqual(error['description'], 'mocked response')

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

    @patch.object(StorageManager, 'pull')
    def test_post(self, mock_pull):
        request = testing.DummyRequest({})
        request.route_url = lambda route, name: 'foo'
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
        }
        request.params = {
            'branch': 'foo',
            'remote': 'bar',
        }
        resource = RepositoryResource(request)

        with patch.object(request.registry, 'notify') as mocked_notify:
            resource.post()
            mock_pull.assert_called_with(branch_name='foo',
                                         remote_name='bar')
            (call1, call2) = mocked_notify.call_args_list
            (event,) = call1[0]
            self.assertIsInstance(event, RepositoryUpdated)
            self.assertEqual(event.repo, self.workspace.repo)
            self.assertEqual(event.branch, 'foo')
            self.assertTrue(event.changes)
            (event,) = call2[0]
            self.assertEqual(event.event_type, 'repo.push')
            self.assertEqual(event.payload, {
                'repo': repo_name,
                'url': 'foo',
            })

    @patch.object(Workspace, 'index_diff')
    def test_update_repo_index(self, mocked_index_diff):
        self.workspace.repo.create_head('foo')
        event = RepositoryUpdated(
            repo=self.workspace.repo,
            config=self.config.registry.settings,
            branch='foo',
            changes='diffindex')

        update_repo_index(event)
        mocked_index_diff.assert_called_with('diffindex')
        self.assertEqual(event.repo.active_branch.name, 'master')

    def test_pull_additions(self):
        upstream_workspace = self.create_upstream_for(self.workspace)
        self.add_schema(upstream_workspace, TestPerson)
        self.add_mapping(upstream_workspace, TestPerson)
        person1 = TestPerson({'age': 1, 'name': 'person1'})
        upstream_workspace.save(person1, 'Adding person1.')

        repo_name = os.path.basename(self.workspace.working_dir)
        request = testing.DummyRequest({})
        request.route_url = lambda route, name: 'foo'
        request.matchdict = {
            'name': repo_name,
        }

        resource = RepositoryResource(request)
        [diff] = resource.post()
        self.assertEqual(diff, {
            'type': 'A',
            'path': upstream_workspace.sm.git_name(person1),
        })

    def test_pull_removals(self):
        upstream_workspace = self.create_upstream_for(self.workspace)
        self.add_schema(upstream_workspace, TestPerson)
        self.add_mapping(upstream_workspace, TestPerson)
        person1 = TestPerson({'age': 1, 'name': 'person1'})
        upstream_workspace.save(person1, 'Adding person1.')
        self.workspace.pull()
        upstream_workspace.delete(person1, 'Removing person1.')

        repo_name = os.path.basename(self.workspace.working_dir)
        request = testing.DummyRequest({})
        request.route_url = lambda route, name: 'foo'
        request.matchdict = {
            'name': repo_name,
        }

        resource = RepositoryResource(request)
        [diff] = resource.post()
        self.assertEqual(diff, {
            'type': 'D',
            'path': upstream_workspace.sm.git_name(person1),
        })

    def test_pull_renames(self):
        upstream_workspace = self.create_upstream_for(self.workspace)
        self.add_schema(upstream_workspace, TestPerson)
        self.add_mapping(upstream_workspace, TestPerson)
        upstream_workspace.sm.store_data(
            'README.rst', 'the readme', 'Writing the readme.')
        self.workspace.pull()
        # do the rename
        upstream_workspace.repo.index.move(['README.rst', 'README.txt'])
        upstream_workspace.repo.index.commit('Renaming rst to txt.')

        repo_name = os.path.basename(self.workspace.working_dir)
        request = testing.DummyRequest({})
        request.route_url = lambda route, name: 'foo'
        request.matchdict = {
            'name': repo_name,
        }

        resource = RepositoryResource(request)
        [diff] = resource.post()
        self.assertEqual(diff, {
            'type': 'R',
            'rename_from': 'README.rst',
            'rename_to': 'README.txt',
        })

    def test_pull_modified(self):
        upstream_workspace = self.create_upstream_for(self.workspace)
        self.add_schema(upstream_workspace, TestPerson)
        self.add_mapping(upstream_workspace, TestPerson)
        person1 = TestPerson({'age': 1, 'name': 'person1'})
        upstream_workspace.save(person1, 'Adding person1.')
        self.workspace.pull()
        updated_person1 = person1.update({'age': 2})
        upstream_workspace.save(updated_person1, 'Updating person1.')

        repo_name = os.path.basename(self.workspace.working_dir)
        request = testing.DummyRequest({})
        request.route_url = lambda route, name: 'foo'
        request.matchdict = {
            'name': repo_name,
        }

        resource = RepositoryResource(request)
        [diff] = resource.post()
        self.assertEqual(diff, {
            'type': 'M',
            'path': upstream_workspace.sm.git_name(person1),
        })

    def test_delete(self):
        repo_name = os.path.basename(self.workspace.working_dir)
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': repo_name,
        }

        resource = RepositoryResource(request)
        resource.delete()
        self.assertEqual(resource.request.response.status_int, 204)
        self.assertFalse(self.workspace.sm.storage_exists())
        self.assertFalse(self.workspace.im.index_exists('master'))


class TestContentTypeResource(DistributeTestCase):

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

        with patch.object(request.registry, 'notify') as mocked_notify:
            object_data = resource.put()
            self.assertEqual(TestPerson(object_data), self.person)
            (event,) = mocked_notify.call_args[0]
            self.assertIsInstance(event, ContentTypeObjectUpdated)
            self.assertEqual(event.repo, self.workspace.repo)
            self.assertEqual(event.model, self.person)
            self.assertEqual(event.change_type, 'update')

    def test_delete(self):
        request = testing.DummyRequest()
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        resource = ContentTypeResource(request)

        with patch.object(request.registry, 'notify') as mocked_notify:
            object_data = resource.delete()
            self.assertEqual(TestPerson(object_data), self.person)
            (event,) = mocked_notify.call_args[0]
            self.assertIsInstance(event, ContentTypeObjectUpdated)
            self.assertEqual(event.repo, self.workspace.repo)
            self.assertEqual(event.model, self.person)
            self.assertEqual(event.change_type, 'delete')

        request = testing.DummyRequest({})
        request.matchdict = {
            'name': os.path.basename(self.workspace.working_dir),
            'content_type': fqcn(TestPerson),
            'uuid': self.person.uuid,
        }
        resource = ContentTypeResource(request)
        self.assertRaises(NotFound, resource.get)

    @patch.multiple(ESManager, unindex=DEFAULT, index=DEFAULT)
    def test_index_content_type_object(self, unindex, index):
        event = ContentTypeObjectUpdated(
            repo=self.workspace.repo,
            model=self.person,
            change_type='update',
            config=self.config.registry.settings)
        index_content_type_object(event)
        index.assert_called_with(self.person)

        event.change_type = 'delete'
        index_content_type_object(event)
        unindex.assert_called_with(self.person)
