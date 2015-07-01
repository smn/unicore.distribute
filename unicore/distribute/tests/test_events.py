from pyramid import testing

from git import Repo

from unicore.distribute.events import (
    RepositoryEvent, RepositoryCloned, RepositoryUpdated,
    ContentTypeObjectUpdated)
from unicore.distribute.tests.base import DistributeTestCase


class TestEvents(DistributeTestCase):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.config = testing.setUp()
        self.config.include('unicore.distribute.api')

    def tearDown(self):
        testing.tearDown()

    def get_handlers_for(self, config, event_cls):
        return map(
            lambda h: h.handler.__name__,
            filter(
                lambda h: h.required[0].implementedBy(event_cls),
                config.registry.registeredHandlers())
            )

    def test_repository_event(self):
        event_obj = RepositoryEvent(
            config='foo config',
            repo_dir=self.workspace.working_dir,
            repo_url='foo url')
        self.assertIsInstance(event_obj.repo, Repo)
        self.assertEqual(event_obj.repo, self.workspace.repo)
        self.assertEqual(event_obj.config, 'foo config')
        self.assertEqual(event_obj.repo_url, 'foo url')

    def test_configuration(self):
        self.assertNotIn('initialize_repo_index',
                         self.get_handlers_for(self.config, RepositoryCloned))
        self.assertNotIn('update_repo_index',
                         self.get_handlers_for(self.config, RepositoryUpdated))
        self.assertNotIn(
            'index_content_type_object',
            self.get_handlers_for(self.config, ContentTypeObjectUpdated))

        config = testing.setUp(settings={
            'es.indexing_enabled': 'true'
        })
        config.include('unicore.distribute.api')
        self.assertIn('initialize_repo_index',
                      self.get_handlers_for(config, RepositoryCloned))
        self.assertIn('update_repo_index',
                      self.get_handlers_for(config, RepositoryUpdated))
        self.assertIn('index_content_type_object',
                      self.get_handlers_for(config, ContentTypeObjectUpdated))
