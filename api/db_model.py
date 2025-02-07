from typing import Any, AsyncGenerator
import uuid
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Integer,
    String,
    UUID,
    DateTime,
    Float,
    ForeignKey,
    Table,
    event,
    select,
    Enum,
    update,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users import schemas
import enum
from .env_config import config

Base = declarative_base()

# Асинхронный URL для PostgreSQL
# postgresql+asyncpg://admin:admin@172.18.0.2/hack
# DATABASE_URL = "postgresql+asyncpg://admin:admin@postgres/hack"
DATABASE_URL = f'postgresql+asyncpg://admin:admin@{config.database_address}/hack'

engine = create_async_engine(
    DATABASE_URL,
    future=True,
    pool_size=2,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


class TransactionStatusEnum(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    balance = Column(Float, default=0)

    __table_args__ = (
        CheckConstraint(
            "balance >= 0", name="check_positive_balance"
        ),  # Проверка, что balance больше 0
    )


class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    job_id = Column(UUID, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    amount = Column(Integer)
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(
        Enum(TransactionStatusEnum), default=TransactionStatusEnum.IN_PROGRESS
    )
    err_reason = Column(String(512), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_file_id = Column(UUID, ForeignKey("uploaded_files.id"))

    uploaded_file = relationship("UploadedFile", back_populates="transaction_history")


class MLModel(Base):
    __tablename__ = "ml_models"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String(64), unique=True)
    model_cost = Column(Float)


class UserRead(schemas.BaseUser[uuid.UUID]):
    balance: float


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class UploadedFile(Base):
    __tablename__ = 'uploaded_files'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False)
    is_deleted = Column(Boolean, default=False)
    any_error_verified = Column(Boolean, default=None)
    any_error_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction_history = relationship("TransactionHistory", back_populates="uploaded_file")
    # users_to_uploaded_files = relationship("UsersToDocuments", back_populates="uploaded_file")

class UsersToDocuments(Base):
    __tablename__ = 'users_to_uploaded_files'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    uploaded_file_id = Column(UUID, ForeignKey("uploaded_files.id"))

    # uploaded_file = relationship("UploadedFile", back_populates="users_to_uploaded_files")

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)

class DocumentsToTags(Base):
    __tablename__ = 'uploaded_files_to_tags'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tag_id = Column('tag_id', Integer, ForeignKey('tags.id'))
    uploaded_file_id = Column('uploaded_file_id', UUID(as_uuid=True), ForeignKey('uploaded_files.id'))


async def create_db_and_tables():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def add_default_values():
    async for session in get_session():
        models_to_add = [
            MLModel(model_name="docs_model", model_cost=0)
        ]

        for model in models_to_add:
            existing_model = (
                await session.execute(
                    select(MLModel).where(MLModel.model_name == model.model_name)
                )
            ).scalar()

            if not existing_model:
                session.add(model)

        await session.commit()


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)





### User Table
# | Column    | Type                  | Default | Constraint                      |
# |-----------|-----------------------|---------|---------------------------------|
# | id        | UUID                  | None    | Primary Key                     |
# | email     | String                | None    | Unique, Not Null                |
# | hashed_password | String          | None    | Not Null                        |
# | is_active | Boolean               | True    |                                 |
# | is_superuser | Boolean            | False   |                                 |
# | balance   | Float                 | 0       | Check: balance >= 0             |
# 
# ### TransactionHistory Table
# | Column        | Type                          | Default       | Constraint              |
# |---------------|-------------------------------|---------------|-------------------------|
# | job_id        | UUID                          | None          | Primary Key, Indexed    |
# | user_id       | UUID                          | None          | Foreign Key (users.id)  |
# | amount        | Integer                       | None          |                         |
# | model_id      | Integer                       | None          | Foreign Key (ml_models.id), Nullable |
# | result        | JSON                          | None          | Nullable                |
# | status        | Enum (TransactionStatusEnum)  | IN_PROGRESS   |                         |
# | err_reason    | String(512)                   | None          | Nullable                |
# | timestamp     | DateTime (timezone=True)      | func.now()    | Server Default          |
# 
# ### MLModel Table
# | Column      | Type         | Default | Constraint      |
# |-------------|--------------|---------|-----------------|
# | id          | Integer      | None    | Primary Key, Indexed, Autoincrement |
# | model_name  | String(64)   | None    | Unique          |
# | model_cost  | Float        | None    |                 |
# 
# ### UploadedFile Table
# | Column             | Type                     | Default   | Constraint                  |
# |--------------------|--------------------------|-----------|-----------------------------|
# | id                 | UUID                     | uuid.uuid4 | Primary Key                 |
# | name               | String(256)              | None      | Not Null                    |
# | is_deleted         | Boolean                  | False     |                             |
# | verified           | Boolean                  | None      |                             |
# | cancellation_reason | String(512)             | None      | Nullable                    |
# | created_at         | DateTime (timezone=True) | func.now() | Server Default              |
# 
# ### UsersToDocuments Table
# | Column       | Type  | Default | Constraint            |
# |--------------|-------|---------|-----------------------|
# | id           | Integer | None  | Primary Key, Indexed, Autoincrement |
# | user_id      | UUID    | None  | Foreign Key (users.id) |
# | uploaded_file_id  | UUID    | None  | Foreign Key (uploaded_files.id) |
# 
# ### Tag Table
# | Column | Type   | Default | Constraint       |
# |--------|--------|---------|------------------|
# | id     | Integer| None    | Primary Key, Indexed, Autoincrement |
# | name   | String | None    | Not Null         |
# 
# ### DocumentsToTags Table
# | Column       | Type    | Default | Constraint                      |
# |--------------|---------|---------|---------------------------------|
# | id           | Integer | None    | Primary Key, Indexed, Autoincrement |
# | tag_id       | Integer | None    | Foreign Key (tags.id)           |
# | uploaded_file_id  | UUID    | None    | Foreign Key (uploaded_files.id)      |
# 