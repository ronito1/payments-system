from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
from app.db import Base


# -----------------------------
# Merchant
# -----------------------------
class Merchant(Base):
    __tablename__ = "merchants"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)


# -----------------------------
# Transaction
# -----------------------------
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"))
    amount = Column(Numeric)
    currency = Column(String)
    status = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# -----------------------------
# Event
# -----------------------------
class Event(Base):
    __tablename__ = "events"
    
    event_id = Column(String, primary_key=True, index=True, unique=True)
    event_type = Column(String, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    merchant_id = Column(String, ForeignKey("merchants.id"))
    amount = Column(Numeric)
    currency = Column(String)
    timestamp = Column(DateTime)
    raw_payload = Column(JSON)