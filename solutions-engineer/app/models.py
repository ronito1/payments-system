from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, JSON, Index
from datetime import datetime, timezone
from app.db import Base


# -----------------------------
# Merchant
# -----------------------------
class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)


# -----------------------------
# Transaction
# -----------------------------
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    amount = Column(Numeric)
    currency = Column(String)
    status = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        # 🔥 composite index for filtering
        Index("idx_txn_merchant_status", "merchant_id", "status"),

        # 🔥 date range queries
        Index("idx_txn_created_at", "created_at"),
    )


# -----------------------------
# Event
# -----------------------------
class Event(Base):
    __tablename__ = "events"
    
    event_id = Column(String, primary_key=True, index=True, unique=True)
    event_type = Column(String, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    amount = Column(Numeric)
    currency = Column(String)
    timestamp = Column(DateTime, index=True)
    raw_payload = Column(JSON)

    __table_args__ = (
        # 🔥 fast lookup for event history
        Index("idx_event_transaction_id", "transaction_id"),

        # 🔥 useful for time-based queries
        Index("idx_event_timestamp", "timestamp"),
    )