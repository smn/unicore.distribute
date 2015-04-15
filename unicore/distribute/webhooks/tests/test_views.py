import unittest

import pytest
import transaction

from pyramid import testing

from sqlalchemy.orm.exc import NoResultFound

from webtest import TestApp

from unicore.distribute.webhooks.models import (
    DBSession, Webhook)
from unicore.distribute.webhooks import views
from unicore.distribute.webhooks import main


@pytest.mark.usefixtures("dbtransaction")
class ModelTestCase(unittest.TestCase):
    pass


class AuthenticatedWebhookTestCase(ModelTestCase):

    def setUp(self):

        self.config = testing.setUp(settings={
            'secret_key': 'hush',
        })
        testing_policy = testing.DummySecurityPolicy(userid=u'the-owner')
        self.config.set_authorization_policy(testing_policy)
        self.config.set_authentication_policy(testing_policy)

        self.anon_webhook = Webhook(
            owner=None,
            url=u'http://example.org/',
            event_type=u'repo.push',
            active=True)
        DBSession.add(self.anon_webhook)

        self.owner_webhook = Webhook(
            owner=u'the-owner',
            url=u'http://example.org/',
            event_type=u'repo.push',
            active=True)
        DBSession.add(self.owner_webhook)

        transaction.commit()
        self.addCleanup(transaction.abort)
        self.addCleanup(testing.tearDown)

    def test_collection_get(self):
        request = testing.DummyRequest()
        resource = views.WebhooksResource(request)
        [webhook] = resource.collection_get()
        self.assertEqual(webhook['uuid'], self.owner_webhook.uuid.hex)

    def test_get(self):
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.owner_webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.get()
        self.assertEqual(webhook['uuid'], self.owner_webhook.uuid.hex)

    def test_get_not_found(self):
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.anon_webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        self.assertRaises(NoResultFound, resource.get)

    def test_delete(self):
        self.assertEqual(DBSession.query(Webhook).count(), 2)
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.owner_webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.delete()
        self.assertEqual(DBSession.query(Webhook).count(), 1)
        self.assertEqual(webhook['uuid'], self.owner_webhook.uuid.hex)

    def test_delete_not_found(self):
        self.assertEqual(DBSession.query(Webhook).count(), 2)
        request = testing.DummyRequest()
        request.matchdict = {
            'uuid': self.anon_webhook.uuid.hex,
        }
        resource = views.WebhooksResource(request)
        self.assertRaises(NoResultFound, resource.delete)
        self.assertEqual(DBSession.query(Webhook).count(), 2)


class AnonymousWebhookTestCase(ModelTestCase):

    def setUp(self):

        self.config = testing.setUp(settings={
            'secret_key': 'hush',
        })

        self.webhook = Webhook(
            url=u'http://example.org',
            event_type=u'repo.push',
            active=True)
        DBSession.add(self.webhook)

        transaction.commit()
        self.addCleanup(transaction.abort)
        self.addCleanup(testing.tearDown)

    def test_collection_get(self):
        request = testing.DummyRequest()
        resource = views.WebhooksResource(request)
        [webhook] = resource.collection_get()
        self.assertEqual(webhook['uuid'], self.webhook.uuid.hex)
        self.assertEqual(webhook['owner'], None)
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
        self.assertEqual(webhook['owner'], None)
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
        self.assertEqual(webhook['owner'], None)
        self.assertEqual(webhook['url'], u'http://example.org')
        self.assertEqual(webhook['event_type'], u'repo.push')
        self.assertEqual(webhook['active'], True)

    def test_collection_post(self):
        self.assertEqual(DBSession.query(Webhook).count(), 1)
        request = testing.DummyRequest()
        request.validated = {
            'url': u'http://www.example.org',
            'event_type': u'repo.push',
            'active': True,
        }
        resource = views.WebhooksResource(request)
        webhook = resource.collection_post()
        self.assertEqual(DBSession.query(Webhook).count(), 2)
        count = DBSession.query(Webhook). \
            filter(Webhook.uuid == webhook['uuid']). \
            count()
        self.assertEqual(count, 1)
        self.assertEqual(webhook['owner'], None)

    def test_update(self):
        webhook = DBSession.query(Webhook).one()
        request = testing.DummyRequest()
        request.validated = {
            'url': 'http://www.example.org/updated/',
            'event_type': u'repo.push',
            'active': False,
        }
        request.matchdict = {
            'uuid': webhook.uuid,
        }
        resource = views.WebhooksResource(request)
        resource.put()
        updated_webhook = DBSession.query(Webhook).one()
        self.assertEqual(updated_webhook.active, False)
        self.assertEqual(
            updated_webhook.url, 'http://www.example.org/updated/')
        self.assertEqual(updated_webhook.event_type, u'repo.push')
        self.assertEqual(updated_webhook.uuid, webhook.uuid)
