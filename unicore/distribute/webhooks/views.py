from cornice.resource import resource, view
from unicore.distribute.utils import get_config

from unicore.distribute.webhooks.models import DBSession, Webhook


@resource(collection_path='/hooks.json', path='/hooks/{uuid}.json')
class WebhooksResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def collection_get(self):
        return [webhook.to_dict()
                for webhook in DBSession.query(Webhook).all()]

view
