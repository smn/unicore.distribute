class WebhookEvent(object):
    def __init__(self, webhook, request):
        self.webhook = webhook
        self.request = request


class WebhookCreated(WebhookEvent):
    pass


class WebhookUpdated(WebhookEvent):
    pass


class WebhookDeleted(WebhookEvent):
    pass


class FireWebhookEvent(object):
    def __init__(self, event_type):
        self.event_type
