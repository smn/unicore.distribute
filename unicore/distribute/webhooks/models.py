from uuid import uuid4

from pyramid.threadlocal import get_current_registry

from sqlalchemy import Column, UnicodeText, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_utils import UUIDType, URLType, ChoiceType

from zope.sqlalchemy import ZopeTransactionExtension


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


def get_key(*args):
    settings = get_current_registry().settings
    return settings['secret_key']


class Webhook(Base):
    __tablename__ = 'webhooks'
    __table_args__ = (
        UniqueConstraint('owner', 'uuid'),
    )

    TYPES = (
        ('repo.push', 'Repository Push'),
    )

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid4)
    owner = Column(UnicodeText, nullable=True)
    url = Column(URLType, nullable=False)
    event_type = Column(ChoiceType(TYPES), nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'uuid': self.uuid.hex,
            'owner': self.owner,
            'url': self.url,
            'event_type': self.event_type.code,
            'active': self.active,
        }
