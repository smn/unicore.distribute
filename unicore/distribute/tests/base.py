import os
import json

from unittest import TestCase

from elasticgit import EG
from elasticgit.commands.avro import serialize
from elasticgit.search import ESManager

from unicore.distribute.utils import get_index_prefix


class DistributeTestCase(TestCase):

    destroy = 'KEEP_REPO' not in os.environ
    WORKING_DIR = '.test_repos/'

    def mk_workspace(self, working_dir=None,
                     name=None,
                     url='http://localhost',
                     index_prefix=None,
                     auto_destroy=None,
                     author_name='Test Kees',
                     author_email='kees@example.org'):  # pragma: no cover
        name = name or self.id()
        working_dir = working_dir or self.WORKING_DIR
        index_prefix = index_prefix or get_index_prefix(name)
        auto_destroy = auto_destroy or self.destroy
        workspace = EG.workspace(os.path.join(working_dir, name), es={
            'urls': [url],
        }, index_prefix=index_prefix)
        if auto_destroy:
            self.addCleanup(workspace.destroy)

        workspace.setup(author_name, author_email)
        while not workspace.index_ready():
            pass

        return workspace

    def add_schema(self, workspace, model_class):
        schema_string = serialize(model_class)
        schema = json.loads(schema_string)
        workspace.sm.store_data(
            os.path.join(
                '_schemas',
                '%(namespace)s.%(name)s.avsc' % schema),
            schema_string, 'Writing the schema.')

    def add_mapping(self, workspace, model_class):
        im = ESManager(None, None, None)
        mapping = im.get_mapping_type(model_class).get_mapping()
        workspace.sm.store_data(
            os.path.join(
                '_mappings',
                '%s.%s.json' % (model_class.__module__,
                                model_class.__name__)),
            json.dumps(mapping), 'Writing the mapping.')

    def mk_model_workspace(self, model_class, *args, **kwargs):
        workspace = self.mk_workspace(*args, **kwargs)
        self.add_schema(workspace, model_class)
        self.add_mapping(workspace, model_class)
        return workspace
