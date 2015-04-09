from uuid import uuid4

from sqlalchemy import Column, ForeignKey, UnicodeText, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_utils import UUIDType, URLType, EncryptedType, ChoiceType

from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


def get_key(*args):
    print 'get_key called with', args
    return 'foo'


class WebhookAccount(Base):
    __tablename__ = 'webhook_accounts'

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid4)
    username = Column(UnicodeText, nullable=False)
    password = Column(EncryptedType(UnicodeText, get_key), nullable=False)


class Webhook(Base):
    __tablename__ = 'webhooks'

    TYPES = (
        ('repo.push', 'Repository Push'),
    )

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid4)
    user = Column(ForeignKey('webhook_accounts.uuid'), nullable=False)
    url = Column(URLType, nullable=False)
    event_type = Column(ChoiceType(TYPES), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
