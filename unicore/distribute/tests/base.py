import os

from unittest import TestCase

from elasticgit import EG

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
