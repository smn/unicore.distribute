import json
from git import Repo
import os
from elasticgit.commands.avro import serialize
from elasticgit.tests.base import ModelBaseTest, TestPerson
from pyramid import testing
from pyramid.exceptions import NotFound
from unicore.distribute.api.repo_status import RepositoryStatusResource, RepositoryDiffResource
from unicore.distribute.utils import format_repo_status, get_repository_diff


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


class TestRepositoryDiffResource(ModelBaseTest):
    initial_commit = ""

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.add_schema(self.workspace, TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })
        self.create_commit("initial commit", True)
        self.add_file(os.path.join(self.workspace.working_dir, "file-1"))
        self.add_file(os.path.join(self.workspace.working_dir, "file-2"))
        self.add_file(os.path.join(self.workspace.working_dir, "file-3"))
        self.create_commit("second commit", False)

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

    def create_commit(self, message, is_initial_commit):
        global initial_commit
        repo = Repo(self.workspace.working_dir)
        repo.commit(repo.index.commit(message))
        if is_initial_commit:
            initial_commit = repo.commit().hexsha

    def add_file(self, filename):
        repo = Repo(self.workspace.working_dir)
        open(filename, 'w+').close()
        repo.index.add([filename])

    def test_get(self):
        global initial_commit
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': initial_commit
        }
        resource = RepositoryDiffResource(request)
        repo_json = resource.get()
        self.assertEqual(repo_json, get_repository_diff(self.workspace.repo, initial_commit))

    def test_get_404(self):
        global initial_commit
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': "1234567"
        }
        resource = RepositoryDiffResource(request)
        self.assertRaises(NotFound, resource.get)
