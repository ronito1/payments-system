from sqlalchemy.orm import Session
from app import models, schemas

def get_merchant(db: Session, merchant_id: int):
    """Retrieve a single merchant by ID."""
    return db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()

def get_merchants(db: Session, skip: int = 0, limit: int = 100):
    """Retrieve a list of merchants with pagination."""
    return db.query(models.Merchant).offset(skip).limit(limit).all()

def create_merchant(db: Session, merchant: schemas.MerchantCreate):
    """Create a new merchant in the database."""
    db_merchant = models.Merchant(name=merchant.name)
    db.add(db_merchant)
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

def get_transaction(db: Session, transaction_id: int):
    """Retrieve a single transaction by ID."""
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    """Create a new transaction in the database."""
    db_transaction = models.Transaction(
        merchant_id=transaction.merchant_id,
        amount=transaction.amount,
        currency=transaction.currency,
        status=transaction.status
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_event(db: Session, event_id: str):
    """Retrieve a single event by its unique event ID."""
    return db.query(models.Event).filter(models.Event.event_id == event_id).first()

def create_event(db: Session, event: schemas.EventCreate):
    """Create a new event record in the database."""
    db_event = models.Event(
        event_id=event.event_id,
        event_type=event.event_type,
        transaction_id=event.transaction_id,
        merchant_id=event.merchant_id,
        amount=event.amount,
        currency=event.currency,
        timestamp=event.timestamp,
        raw_payload=event.raw_payload
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
