from urlparse import urljoin

from pyramid.response import Response
from pyramid.httpexceptions import HTTPNotFound

import requests


class Proxy(object):

    def __init__(self, upstream_url):
        self.upstream_url = upstream_url

    def __call__(self, request):
        view = ProxyView(request, self.upstream_url)
        handler = getattr(view, 'do_%s' % (request.method,), HTTPNotFound)
        return handler()


class ProxyView(object):

    def __init__(self, request, upstream_url):
        self.request = request
        self.upstream_url = upstream_url

    def url(self):
        return urljoin(self.upstream_url, self.request.matchdict['parts'])

    def mk_request(self, *args, **kwargs):  # for mocking
        return requests.request(*args, **kwargs)

    def mk_response(self, response):
        return Response(body=response.text, status=response.status_code,
                        headerlist=response.headers.items(),
                        content_type=response.headers['Content-Type'],
                        charset=response.encoding)

    def do_request(self):
        return self.mk_response(
            self.mk_request(
                self.request.method, self.url(), data=self.request.body))

    def do_POST(self):
        return self.do_request()

    def do_DELETE(self):
        return self.do_request()

    def do_PUT(self):
        return self.do_request()

    def do_GET(self):
        return self.do_request()

    def do_HEAD(self):
        return self.do_request()
