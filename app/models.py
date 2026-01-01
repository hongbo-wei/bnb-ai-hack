from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase

from app.config import VECTOR_DIM


class Base(DeclarativeBase):
    pass


class OnChainEvent(Base):
    __tablename__ = "onchain_events"

    id = Column(Integer, primary_key=True)
    tx_hash = Column(String(80), unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    chain = Column(String(32), default="bnb")
    from_address = Column(String(64), nullable=True)
    to_address = Column(String(64), nullable=True)
    value = Column(Float, nullable=True)
    block_number = Column(Integer, nullable=True)
    tags = Column(Text, nullable=True)
    embedding = Column(Vector(VECTOR_DIM), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class MCPDecision(Base):
    __tablename__ = "mcp_decisions"

    id = Column(Integer, primary_key=True)
    route = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserTrade(Base):
    __tablename__ = "user_trades"
    __table_args__ = (UniqueConstraint("user_id", "external_id", name="user_trades_user_external_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    asset = Column(String(32), nullable=False)
    side = Column(String(8), nullable=False)
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    external_id = Column(String(128), nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class UserHolding(Base):
    __tablename__ = "user_holdings"
    __table_args__ = (UniqueConstraint("user_id", "asset", name="user_holdings_user_asset"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    asset = Column(String(32), nullable=False)
    quantity = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
