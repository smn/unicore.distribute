from colander import (
    MappingSchema, SchemaNode, String, Invalid, Boolean, OneOf, url)

from cornice.resource import resource, view

from unicore.distribute.utils import get_config
from unicore.distribute.webhooks.models import DBSession, Webhook


class CreateWebhookSchema(MappingSchema):
    url = SchemaNode(String(), location='body', validator=url)
    event_type = SchemaNode(
        String(), location='body',
        validator=OneOf([value for value, label in Webhook.TYPES]))
    active = SchemaNode(Boolean(), location='body')


@resource(collection_path='/hooks.json', path='/hooks/{uuid}.json')
class WebhooksResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def collection_get(self):
        return [webhook.to_dict()
                for webhook in DBSession.query(Webhook).all()]

    @view(renderer='json')
    def get(self):
        return DBSession. \
            query(Webhook). \
            filter(Webhook.uuid == self.request.matchdict['uuid']). \
            one(). \
            to_dict()

    @view(renderer='json')
    def delete(self):
        webhook = DBSession. \
            query(Webhook). \
            filter(Webhook.uuid == self.request.matchdict['uuid']). \
            one()
        data = webhook.to_dict()
        DBSession.delete(webhook)
        return data

    @view(renderer='json', schema=CreateWebhookSchema)
    def post(self):
        url = self.request.validated['url']
        event_type = self.request.validated['event_type']
        active = self.request.validated['active']
        webhook = Webhook(url=url, event_type=event_type, active=active)
        DBSession.add(webhook)
        return webhook.to_dict()
