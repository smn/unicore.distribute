import json
import os

from elasticgit.tests.base import TestPerson, ModelBaseTest
from elasticgit.commands.avro import serialize

from pyramid import testing

from unicore.distribute.api.repos import RepositoryResource
from unicore.distribute.utils import format_repo


class TestRepos(ModelBaseTest):

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

    def test_repos_collection(self):
        request = testing.DummyRequest({})
        resource = RepositoryResource(request)
        [repo_json] = resource.collection_get()
        self.assertEqual(repo_json, format_repo(self.workspace.repo))
