#type: ignore

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import abc
from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
import uuid

SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@postgres:{settings.DATABASE_PORT}/{settings.POSTGRES_DB}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=32,
    max_overflow=64
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base_var = declarative_base()


class Base(Base_var):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False,
                default=uuid.uuid4)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text("now()"))
    # updated_at = Column(TIMESTAMP(timezone=True),
#                     nullable=False, server_default=text("now()"))

class Base_del():
    __abstract__ = True
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, default=None)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

