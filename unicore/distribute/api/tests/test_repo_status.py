import json
from elasticgit import EG
from git import Repo
import os
from elasticgit.commands.avro import serialize
from elasticgit.tests.base import ModelBaseTest, TestPerson
from pyramid import testing
from pyramid.exceptions import NotFound
from unicore.distribute.api.repo_status import (
    RepositoryStatusResource, RepositoryDiffResource, RepositoryPullResource)
from unicore.distribute.utils import (
    format_repo_status, get_repository_diff, pull_repository_files)


class TestRepositoryStatusResource(ModelBaseTest):
    def setUp(self):
        self.workspace = self.mk_workspace()
        self.add_schema(self.workspace, TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })
        self.addCleanup(lambda: EG.workspace(self.WORKING_DIR).destroy())

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
        [repo_json] = resource.collection_get()
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
        self.initial_commit = self.create_commit("initial commit")
        person1 = TestPerson({'age': 12, 'name': 'Foo'})
        person2 = TestPerson({'age': 34, 'name': 'Bar'})
        self.workspace.save(person1, "saving person 1")
        self.workspace.save(person2, "saving person 2")
        self.create_commit("second commit")
        self.addCleanup(lambda: EG.workspace(self.WORKING_DIR).destroy())

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

    def create_commit(self, message):
        repo = Repo(self.workspace.working_dir)
        repo.commit(repo.index.commit(message))
        return repo.commit().hexsha

    def test_get(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': self.initial_commit
        }
        resource = RepositoryDiffResource(request)
        repo_json = resource.get()
        self.assertEqual(repo_json, get_repository_diff(
            self.workspace.repo, self.initial_commit))

    def test_get_404(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': 1234567
        }
        resource = RepositoryDiffResource(request)
        self.assertRaises(NotFound, resource.get)


class TestRepositoryPullResource(ModelBaseTest):
    initial_commit = ""

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.add_schema(self.workspace, TestPerson)
        self.config = testing.setUp(settings={
            'repo.storage_path': self.WORKING_DIR,
        })
        self.initial_commit = self.create_commit("initial commit")
        person1 = TestPerson({'age': 12, 'name': 'Foo'})
        person2 = TestPerson({'age': 34, 'name': 'Bar'})
        self.workspace.save(person1, "saving person 1")
        self.workspace.save(person2, "saving person 2")
        self.create_commit("second commit")
        self.addCleanup(lambda: EG.workspace(self.WORKING_DIR).destroy())

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

    def create_commit(self, message):
        repo = Repo(self.workspace.working_dir)
        repo.index.commit(message)
        return repo.commit().hexsha

    def test_get(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': self.initial_commit
        }
        resource = RepositoryPullResource(request)
        repo_json = resource.get()
        self.assertEqual(repo_json, pull_repository_files(
            self.workspace.repo, self.initial_commit))

    def test_get_404(self):
        request = testing.DummyRequest({})
        repo_name = os.path.basename(self.workspace.working_dir)
        request.matchdict = {
            'name': repo_name,
            'commit_id': '12345678'
        }
        resource = RepositoryPullResource(request)
        self.assertRaises(NotFound, resource.get)
