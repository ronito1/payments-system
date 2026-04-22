from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime
from typing import List

from app import models
from app.db import engine, get_db
from app.models import Event, Transaction, Merchant
from app.schemas import EventCreate

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Reconciliation System")


# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Welcome to the Payment Reconciliation API"}


# -----------------------------
# DB TEST
# -----------------------------
@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).fetchone()
    return {"status": "connected", "result": str(result)}


# -----------------------------
# SINGLE EVENT INGESTION
# -----------------------------
@app.post("/events")
def ingest_event(event: EventCreate, db: Session = Depends(get_db)):

    existing = db.query(Event).filter(Event.event_id == event.event_id).first()
    if existing:
        return {"message": "Duplicate event ignored"}

    merchant = db.query(Merchant).filter(Merchant.id == event.merchant_id).first()
    if not merchant:
        merchant = Merchant(
            id=event.merchant_id,
            name=event.merchant_name or ""
        )
        db.add(merchant)

    txn = db.query(Transaction).filter(Transaction.id == event.transaction_id).first()
    if not txn:
        txn = Transaction(
            id=event.transaction_id,
            merchant_id=event.merchant_id,
            amount=event.amount,
            currency=event.currency,
            status="initiated",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(txn)

    db.flush()

    new_event = Event(
        event_id=event.event_id,
        event_type=event.event_type,
        transaction_id=event.transaction_id,
        merchant_id=event.merchant_id,
        amount=event.amount,
        currency=event.currency,
        timestamp=event.timestamp,
        raw_payload=event.model_dump(mode="json")
    )
    db.add(new_event)

    if event.event_type == "payment_initiated":
        txn.status = "initiated"
    elif event.event_type == "payment_processed":
        txn.status = "processed"
    elif event.event_type == "payment_failed":
        txn.status = "failed"
    elif event.event_type == "settled":
        txn.status = "settled"

    txn.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Event processed successfully"}


# -----------------------------
# BULK INGESTION (FIXED)
# -----------------------------
@app.post("/events/bulk")
def ingest_bulk(events: List[EventCreate], db: Session = Depends(get_db)):

    processed = 0
    skipped = 0

    seen_event_ids = set()  # 🔥 fix for in-batch duplicates

    for event in events:

        # 🚨 skip duplicates inside same batch
        if event.event_id in seen_event_ids:
            skipped += 1
            continue
        seen_event_ids.add(event.event_id)

        # skip duplicates already in DB
        existing = db.query(Event).filter(Event.event_id == event.event_id).first()
        if existing:
            skipped += 1
            continue

        merchant = db.query(Merchant).filter(Merchant.id == event.merchant_id).first()
        if not merchant:
            merchant = Merchant(
                id=event.merchant_id,
                name=event.merchant_name or ""
            )
            db.add(merchant)

        txn = db.query(Transaction).filter(Transaction.id == event.transaction_id).first()
        if not txn:
            txn = Transaction(
                id=event.transaction_id,
                merchant_id=event.merchant_id,
                amount=event.amount,
                currency=event.currency,
                status="initiated",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(txn)

        db.flush()

        new_event = Event(
            event_id=event.event_id,
            event_type=event.event_type,
            transaction_id=event.transaction_id,
            merchant_id=event.merchant_id,
            amount=event.amount,
            currency=event.currency,
            timestamp=event.timestamp,
            raw_payload=event.model_dump(mode="json")
        )
        db.add(new_event)

        # status update
        if event.event_type == "payment_initiated":
            txn.status = "initiated"
        elif event.event_type == "payment_processed":
            txn.status = "processed"
        elif event.event_type == "payment_failed":
            txn.status = "failed"
        elif event.event_type == "settled":
            txn.status = "settled"

        txn.updated_at = datetime.utcnow()

        processed += 1

    db.commit()

    return {
        "processed": processed,
        "skipped_duplicates": skipped
    }


# -----------------------------
# TRANSACTIONS LIST
# -----------------------------
@app.get("/transactions")
def get_transactions(db: Session = Depends(get_db)):
    txns = db.query(Transaction).all()

    return [
        {
            "id": t.id,
            "merchant_id": t.merchant_id,
            "amount": float(t.amount),
            "currency": t.currency,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        for t in txns
    ]


# -----------------------------
# SINGLE TRANSACTION
# -----------------------------
@app.get("/transactions/{txn_id}")
def get_transaction(txn_id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()

    if not txn:
        return {"error": "Transaction not found"}

    return {
        "id": txn.id,
        "merchant_id": txn.merchant_id,
        "amount": float(txn.amount),
        "currency": txn.currency,
        "status": txn.status,
        "created_at": txn.created_at,
        "updated_at": txn.updated_at
    }


# -----------------------------
# SUMMARY
# -----------------------------
@app.get("/reconciliation/summary")
def get_summary(db: Session = Depends(get_db)):

    total = db.query(func.count(Transaction.id)).scalar()
    success = db.query(func.count(Transaction.id))\
        .filter(Transaction.status == "settled").scalar()
    failed = db.query(func.count(Transaction.id))\
        .filter(Transaction.status == "failed").scalar()
    total_amount = db.query(func.sum(Transaction.amount)).scalar()

    return {
        "total_transactions": total,
        "successful_transactions": success,
        "failed_transactions": failed,
        "total_amount": float(total_amount or 0)
    }


# -----------------------------
# DISCREPANCIES
# -----------------------------
@app.get("/reconciliation/discrepancies")
def get_discrepancies(db: Session = Depends(get_db)):

    problematic = db.query(Transaction)\
        .filter(Transaction.status == "initiated")\
        .all()

    return [
        {
            "transaction_id": t.id,
            "merchant_id": t.merchant_id,
            "status": t.status,
            "issue": "Transaction stuck in initiated state"
        }
        for t in problematic
    ]