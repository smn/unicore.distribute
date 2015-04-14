import json
import unittest

import pytest
import transaction

from pyramid import testing

from unicore.distribute.webhooks.models import (
    DBSession, Webhook)
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


class WebhookTestCase(ModelTestCase):

    def setUp(self):
        self.webhook = Webhook(
            owner=u'the owner', url=u'http://example.org',
            event_type=u'repo.push', active=True)
        DBSession.add(self.webhook)
        transaction.commit()

    def test_collection_get(self):
        request = testing.DummyRequest()
        resource = views.WebhooksResource(request)
        [webhook] = resource.collection_get()
        self.assertEqual(webhook['uuid'], self.webhook.uuid.hex)
        self.assertEqual(webhook['owner'], u'the owner')
        self.assertEqual(webhook['url'], u'http://example.org')
        self.assertEqual(webhook['event_type'], u'repo.push')
        self.assertEqual(webhook['active'], True)

    def test_get(self):
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.get()
        self.assertEqual(webhook['uuid'], self.webhook.uuid.hex)
        self.assertEqual(webhook['owner'], u'the owner')
        self.assertEqual(webhook['url'], u'http://example.org')
        self.assertEqual(webhook['event_type'], u'repo.push')
        self.assertEqual(webhook['active'], True)

    def test_delete(self):
        self.assertEqual(DBSession.query(Webhook).count(), 1)
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.delete()
        self.assertEqual(DBSession.query(Webhook).count(), 0)
        self.assertEqual(webhook['uuid'], self.webhook.uuid.hex)
        self.assertEqual(webhook['owner'], u'the owner')
        self.assertEqual(webhook['url'], u'http://example.org')
        self.assertEqual(webhook['event_type'], u'repo.push')
        self.assertEqual(webhook['active'], True)

    def test_post(self):
        self.assertEqual(DBSession.query(Webhook).count(), 1)
        request = testing.DummyRequest()
        request.validated = {
            'url': u'http://www.example.org',
            'event_type': u'repo.push',
            'active': True,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.post()
        self.assertEqual(DBSession.query(Webhook).count(), 2)
        count = DBSession.query(Webhook). \
            filter(Webhook.uuid == webhook['uuid']). \
            count()
        self.assertEqual(count, 1)
