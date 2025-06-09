
import uuid
from .database import Base, Base_var, Base_del
from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, Boolean, text, Integer, Float, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from enum import Enum

class UserRole(Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class StatusOrders(Enum): # Надо будет обновить, когда расскажут поподробнее
    NEW = "NEW"
    OLD = "OLD"

class DirectionsOrders(Enum): # Надо будет обновить, когда расскажут поподробнее
    BUY = "BUY"
    SELL = "SELL"

class User(Base):
    __tablename__ = 'users'
    name = Column(String,  nullable=False)
    role = Column(ENUM(UserRole, name="user_role_enum", create_type=False), server_default="USER", nullable=False)
    balance = relationship('Balance')
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, default=None)


class Instrument(Base):
    __tablename__ = 'instruments'
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, default=None)



class Order(Base):
    __tablename__ = 'orders'
    # status = Column(ENUM())
    user_id = Column(UUID(as_uuid=True),ForeignKey(User.id), primary_key=True, nullable=False,
                default=uuid.uuid4)
    user = relationship('User')
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, nullable=False, default=0)
    price = Column(Float, nullable=True)
    filled = Column(Boolean, nullable=False, server_default='False')
    instrument_id = Column(UUID(as_uuid=True),ForeignKey(Instrument.id), primary_key=True, nullable=False,
                default=uuid.uuid4)
    instrument = relationship('Instrument')
    direction = Column(ENUM(DirectionsOrders, name="order_direction_enum", create_type=False), nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, default=None)
    # cancelled = Column(Boolean, nullable=False, default=False)


class Balance(Base_var):
    __tablename__ = 'balance'
    
    user_id = Column(UUID(as_uuid=True),ForeignKey(User.id), primary_key=True, nullable=False)
    instrument_id = Column(UUID(as_uuid=True),ForeignKey(Instrument.id), primary_key=True, nullable=False)
    amount = Column(Float, nullable=False, default=0)
    locked = Column(Float, nullable=False, default=0)


class Transaction(Base):
    __tablename__ = 'transactions'

    instrument_id = Column(UUID(as_uuid=True),ForeignKey(Instrument.id), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(UUID(as_uuid=True),ForeignKey(Instrument.id), nullable=False)
    currency_amount = Column(Float, nullable=False)