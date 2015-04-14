from uuid import uuid4

from pyramid.threadlocal import get_current_registry

from sqlalchemy import Column, ForeignKey, UnicodeText, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_utils import UUIDType, URLType, EncryptedType, ChoiceType

from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


def get_key(*args):
    settings = get_current_registry().settings
    return settings['secret_key']


class WebhookAccount(Base):
    __tablename__ = 'webhook_accounts'

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid4)
    username = Column(UnicodeText, nullable=False)
    password = Column(EncryptedType(UnicodeText, get_key), nullable=False)

    def to_dict(self):
        return {
            'uuid': self.uuid.hex,
            'username': self.username,
            'password': self.password,
        }


class Webhook(Base):
    __tablename__ = 'webhooks'

    TYPES = (
        ('repo.push', 'Repository Push'),
    )

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid4)
    account = Column(ForeignKey('webhook_accounts.uuid'), nullable=False)
    url = Column(URLType, nullable=False)
    event_type = Column(ChoiceType(TYPES), nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'uuid': self.uuid.hex,
            'account': self.account.hex,
            'url': self.url,
            'event_type': self.event_type,
            'active': self.active,
        }
