from pyramid.config import Configurator

from unicore.distribute.api import proxy


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('unicore.distribute.api')
    return config.make_wsgi_app()


def includeme(config):
    config.include('cornice')
    config.scan('.repos')
    config.add_route('esapi', '/esapi/{parts:.*}')
    config.add_view(proxy.Proxy('http://localhost:9200/'), route_name='esapi')
