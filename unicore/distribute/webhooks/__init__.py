from __future__ import absolute_import

from psycopg2cffi import compat
compat.register()

# See: http://sqlalchemy-utils.readthedocs.org/en/latest/listeners.html
from sqlalchemy_utils import force_auto_coercion, force_instant_defaults
force_auto_coercion()
force_instant_defaults()

from sqlalchemy import engine_from_config
from unicore.distribute.webhooks.models import DBSession


def includeme(config):
    settings = config.registry.settings
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
