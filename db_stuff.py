from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

import os

connection_string = os.environ.get("CONNECTION_STRING")
Base = declarative_base()


class Subscription(Base):

    __tablename__ = 'subscriptions'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(String)
    crypto = Column(String)

    __table_args__ = (
        UniqueConstraint('user_id', 'crypto')
    )
