import json
import os
from elasticgit.commands.avro import serialize
from elasticgit.tests.base import ModelBaseTest, TestPerson
from pyramid import testing
from pyramid.exceptions import NotFound
from unicore.distribute.api.repo_status import RepositoryStatusResource
from unicore.distribute.utils import format_repo_status


class TestRepositoryStatusResource(ModelBaseTest):
    def setUp(self):
        self.workspace = self.mk_workspace()
        self.add_schema(self.workspace, TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

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
        resource = RepositoryStatusResource(request)
        foo = resource.collection_get()
        print foo
        [repo_json] = foo
        self.assertEqual(repo_json, format_repo_status(self.workspace.repo))

    def test_get(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
        }
        resource = RepositoryStatusResource(request)
        repo_json = resource.get()
        self.assertEqual(repo_json, format_repo_status(self.workspace.repo))

    def test_get_404(self):
        request = testing.DummyRequest({})
        request.matchdict = {
            'name': 'does-not-exist',
        }
        resource = RepositoryStatusResource(request)
        self.assertRaises(NotFound, resource.get)
