from pyramid.view import view_config
from pyramid.response import Response


class ProxyView(object):

    def __init__(self, request):
        self.request = request

    @view_config(route_name='esapi')
    def esapi(self):
        return Response('hello!! %s' % (self.request.matchdict,))
