import unittest

import pytest
import transaction

from pyramid import testing

from unicore.distribute.webhooks.models import (
    DBSession, WebhookAccount, Webhook)
from unicore.distribute.webhooks import views


@pytest.mark.usefixtures("dbtransaction")
class ModelTestCase(unittest.TestCase):

    def setup_method(self, method):
        self.config = testing.setUp(settings={
            'secret_key': 'hush',
        })

    def teardown_method(self, method):
        transaction.abort()
        testing.tearDown()


class WebhookAccountTestCase(ModelTestCase):

    def setUp(self):
        self.account = WebhookAccount(username=u'foo', password=u'bar')
        self.webhook = Webhook(
            account=self.account.uuid, url=u'http://example.org',
            event_type=u'repo.push', active=True)
        DBSession.add(self.account)
        DBSession.add(self.webhook)
        transaction.commit()

        self.request = testing.DummyRequest()
        self.resource = views.WebhooksResource(self.request)

    def test_collection_get(self):
        [webhook] = self.resource.collection_get()
        self.assertEqual(webhook['uuid'], self.webhook.uuid.hex)
        self.assertEqual(webhook['account'], self.account.uuid.hex)
        self.assertEqual(webhook['url'], u'http://example.org')
        self.assertEqual(webhook['event_type'], u'repo.push')
        self.assertEqual(webhook['active'], True)
