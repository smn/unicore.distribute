from pyramid.config import Configurator


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('unicore.distribute.api', 'foo')
    return config.make_wsgi_app()


def includeme(config):
    config.include('cornice')
    config.scan('unicore.distribute.api.repos')

    # Dynamically load any stuff that's optionally included.
    settings = config.registry.settings
    api_includes = settings['unicore.distribute.includes'].strip().split('\n')
    for include in api_includes:
        config.include(include)
