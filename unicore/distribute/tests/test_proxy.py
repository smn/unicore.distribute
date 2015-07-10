from unittest import TestCase

from mock import Mock, patch

from pyramid import testing
from pyramid.request import Request
from webtest import TestApp

from requests.models import Response

from unicore.distribute.api.proxy import ProxyView, Proxy
from unicore.distribute.api import main


class TestProxy(TestCase):

    def mk_proxy_view(self,
                      url='http://example.org',
                      method='GET',
                      response_content='',
                      content_type='application/json',
                      encoding='utf-8',
                      parts=''):
        request = Request.blank('/', base_url=url, method=method)
        request.matchdict = {
            'parts': parts,
        }

        proxy_view = ProxyView(request, url)
        response = Response()
        response.headers['Content-Type'] = content_type
        response._content = response_content
        response.encoding = encoding
        mock = Mock()
        mock.return_value = response
        proxy_view.mk_request = mock
        return proxy_view

    def mk_proxy_request(self, method, response_content=''):
        proxy_view = self.mk_proxy_view(
            'http://example.org', response_content=response_content)
        return getattr(proxy_view, 'do_%s' % (method,))()

    def test_proxy_view(self):
        proxy_view = self.mk_proxy_view('http://example.org')
        self.assertTrue(isinstance(proxy_view, ProxyView))

    def test_do_POST(self):
        proxy_view = self.mk_proxy_view(method='POST')
        proxy_view.do_POST()
        proxy_view.mk_request.assert_called_with(
            'POST', 'http://example.org', data='')

    def test_do_GET(self):
        proxy_view = self.mk_proxy_view(method='GET')
        proxy_view.do_GET()
        proxy_view.mk_request.assert_called_with(
            'GET', 'http://example.org', data='')

    def test_do_DELETE(self):
        proxy_view = self.mk_proxy_view(method='DELETE')
        proxy_view.do_DELETE()
        proxy_view.mk_request.assert_called_with(
            'DELETE', 'http://example.org', data='')

    def test_do_PUT(self):
        proxy_view = self.mk_proxy_view(method='PUT')
        proxy_view.do_PUT()
        proxy_view.mk_request.assert_called_with(
            'PUT', 'http://example.org', data='')

    def test_do_HEAD(self):
        proxy_view = self.mk_proxy_view(method='HEAD')
        proxy_view.do_HEAD()
        proxy_view.mk_request.assert_called_with(
            'HEAD', 'http://example.org', data='')

    def test_unsupported_methods(self):
        request = Request.blank(
            '/', base_url='http://www.example.org', method='PATCH')
        request.matchdict = {'parts': 'foo'}

        proxy = Proxy('http://example.org')
        resp = proxy(request)
        self.assertEqual(resp.status_code, 404)

    def test_url(self):
        proxy_view = self.mk_proxy_view(parts='foo')
        proxy_view.do_GET()
        proxy_view.mk_request.assert_called_with(
            'GET', 'http://example.org/foo', data='')

    @patch.object(ProxyView, 'mk_request')
    def test_proxy_setup(self, mocked_request):
        response = Response()
        response.headers['Content-Type'] = 'application/text'
        response._content = 'hello world'
        response.encoding = 'utf-8'
        mocked_request.return_value = response
        settings = {'proxy.enabled': 'true',
                    'proxy.path': '/esapi'}
        testing.setUp(settings=settings)
        app = TestApp(main({}, **settings))
        response = app.get('/esapi/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/text')
        self.assertEqual(response.body, 'hello world')
