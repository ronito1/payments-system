from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


# -----------------------------
# Merchant
# -----------------------------
class MerchantBase(BaseModel):
    name: str


class MerchantCreate(MerchantBase):
    id: str


class Merchant(MerchantBase):
    id: str

    class Config:
        from_attributes = True


# -----------------------------
# Transaction
# -----------------------------
class TransactionBase(BaseModel):
    merchant_id: str
    amount: float
    currency: str
    status: str


class TransactionCreate(TransactionBase):
    id: str


class Transaction(TransactionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------
# Event
# -----------------------------
class EventBase(BaseModel):
    event_id: str
    event_type: str
    transaction_id: str
    merchant_id: str
    amount: float
    currency: str
    timestamp: datetime
    raw_payload: Optional[Any] = None


class EventCreate(BaseModel):
    event_id: str
    event_type: str
    transaction_id: str
    merchant_id: str
    merchant_name: Optional[str] = None
    amount: float
    currency: str
    timestamp: datetime


class Event(EventBase):
    class Config:
        from_attributes = True