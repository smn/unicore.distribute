from pyramid.config import Configurator


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('unicore.distribute.api')
    return config.make_wsgi_app()


def includeme(config):
    config.include('cornice')
    config.add_route('esapi', '/esapi/{parts:.*}')
    config.scan('.repos')
    config.scan('.search')
