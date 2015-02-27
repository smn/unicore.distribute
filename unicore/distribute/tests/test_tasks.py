from unicore.distribute.tests.base import DistributeTestCase
from unicore.distribute.tasks import fastforward

from unicore.content.models import Page


class TestTasks(DistributeTestCase):

    def setUp(self):
        self.local_workspace = self.mk_workspace()
        self.remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.id().lower(),),
            index_prefix='%s_remote' % (self.local_workspace.index_prefix,))

    def test_fastforward(self):
        page1 = Page({
            'title': 'foo'
        })
        page2 = Page({
            'title': 'bar'
        })

        self.remote_workspace.save(page1, 'Saving page1.')
        self.remote_workspace.save(page2, 'Saving page2.')

        self.local_workspace.repo.create_remote(
            'origin', self.remote_workspace.working_dir)

        self.assertEqual(
            self.local_workspace.S(Page).count(), 0)
        fastforward(self.local_workspace.working_dir,
                    self.local_workspace.index_prefix)
        self.assertEqual(
            self.local_workspace.S(Page).count(), 2)
