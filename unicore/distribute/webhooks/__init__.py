from __future__ import absolute_import

# See: http://sqlalchemy-utils.readthedocs.org/en/latest/listeners.html
from sqlalchemy_utils import force_auto_coercion, force_instant_defaults
force_auto_coercion()
force_instant_defaults()

from sqlalchemy import engine_from_config
from unicore.distribute.webhooks.models import DBSession, Base

# from pyramid.authentication import BasicAuthAuthenticationPolicy
# from pyramid.authorization import ACLAuthorizationPolicy


def includeme(config):
    settings = config.registry.settings
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    # authn_policy = BasicAuthAuthenticationPolicy(
    #     credentials_check, realm='Webhooks', debug=False)
    # authz_policy = ACLAuthorizationPolicy()
    # config.set_authentication_policy(authn_policy)
    # config.set_authorization_policy(authz_policy)
    config.scan('unicore.distribute.webhooks.views')
