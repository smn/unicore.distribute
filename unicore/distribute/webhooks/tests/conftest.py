import os

import pytest

from sqlalchemy import engine_from_config

from unicore.distribute.webhooks.models import DBSession, Base

from pyramid.paster import get_appsettings, setup_logging


def pytest_addoption(parser):
    parser.addoption("--ini",
                     action="store",
                     metavar="INI_FILE",
                     help="use INI_FILE to configure SQLAlchemy")


@pytest.fixture(scope='session')
def appsettings(request):
    config_uri = os.path.abspath(request.config.option.ini)
    setup_logging(config_uri)
    return get_appsettings(config_uri)


@pytest.fixture(scope='session')
def sqlengine(request, appsettings):
    engine = engine_from_config(appsettings, 'sqlalchemy.')
    DBSession.configure(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)

    request.addfinalizer(teardown)
    return engine


@pytest.fixture()
def dbtransaction(request, sqlengine):
    connection = sqlengine.connect()
    transaction = connection.begin()
    DBSession.configure(bind=connection, expire_on_commit=False)

    def teardown():
        transaction.rollback()
        connection.close()
        DBSession.remove()

    request.addfinalizer(teardown)

    return connection
