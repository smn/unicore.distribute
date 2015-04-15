from colander import (
    MappingSchema, SchemaNode, String, Boolean, OneOf, url)

from cornice.resource import resource, view

from pyramid import httpexceptions
from pyramid.view import view_config

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from unicore.distribute.utils import get_config
from unicore.distribute.webhooks.models import DBSession, Webhook
from unicore.distribute.webhooks.events import (
    WebhookDeleted, WebhookCreated, WebhookUpdated)


class WebhookSchema(MappingSchema):
    url = SchemaNode(String(), location='body', validator=url)
    event_type = SchemaNode(
        String(), location='body',
        validator=OneOf([value for value, label in Webhook.TYPES]))
    active = SchemaNode(Boolean(), location='body')


# Raise SQLAlchemy exceptions as HTTP 404s
@view_config(context=NoResultFound)
@view_config(context=MultipleResultsFound)
def sqlachemy_error(exception, request):
    raise httpexceptions.HTTPNotFound()


@resource(collection_path='/hooks.json', path='/hooks/{uuid}.json')
class WebhooksResource(object):

    def __init__(self, request):
        self.request = request
        self.webhooks = DBSession.query(Webhook). \
            filter(Webhook.owner == request.authenticated_userid)
        self.config = get_config(request)

    # @view(renderer='json')
    def collection_get(self):
        return [webhook.to_dict()
                for webhook in self.webhooks.all()]

    # @view(renderer='json')
    def get(self):
        return self.webhooks. \
            filter(Webhook.uuid == self.request.matchdict['uuid']). \
            one(). \
            to_dict()

    # @view(renderer='json')
    def delete(self):
        webhook = self.webhooks. \
            filter(Webhook.uuid == self.request.matchdict['uuid']). \
            one()
        data = webhook.to_dict()
        DBSession.delete(webhook)
        self.request.registry.notify(WebhookDeleted(webhook, self.request))
        return data

    # @view(renderer='json', schema=WebhookSchema)
    def post(self):
        url = self.request.validated['url']
        event_type = self.request.validated['event_type']
        active = self.request.validated['active']
        webhook = Webhook(owner=self.request.authenticated_userid,
                          url=url,
                          event_type=event_type,
                          active=active)
        DBSession.add(webhook)
        self.request.registry.notify(WebhookCreated(webhook, self.request))
        return webhook.to_dict()

    # @view(renderer='json', schema=WebhookSchema)
    def put(self):
        webhook = self.webhooks. \
            filter(Webhook.uuid == self.request.matchdict['uuid']). \
            one()
        webhook.url = self.request.validated['url']
        webhook.event_type = self.request.validated['event_type']
        webhook.active = self.request.validated['active']
        self.request.registry.notify(WebhookUpdated(webhook, self.request))
        return webhook.to_dict()
