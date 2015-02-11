import os

from unittest import TestCase

from slugify import slugify

from elasticgit import EG


class DistributeTestCase(TestCase):

    destroy = 'KEEP_REPO' not in os.environ
    working_dir = '.test_repos/'

    def mk_workspace(self, working_dir=None,
                     name=None,
                     url='http://localhost',
                     index_prefix=None,
                     auto_destroy=None,
                     author_name='Test Kees',
                     author_email='kees@example.org'):  # pragma: no cover
        name = name or self.id()
        working_dir = working_dir or self.working_dir
        index_prefix = index_prefix or slugify(name)
        auto_destroy = auto_destroy or self.destroy
        workspace = EG.workspace(os.path.join(working_dir, name), es={
            'urls': [url],
        }, index_prefix=index_prefix)
        if auto_destroy:
            self.addCleanup(workspace.destroy)

        workspace.setup(author_name, author_email)
        workspace
        while not workspace.index_ready():
            pass

        return workspace
