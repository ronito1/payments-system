from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime
from typing import List, Optional

from app import models
from app.db import engine, get_db
from app.models import Event, Transaction, Merchant
from app.schemas import EventCreate

# ✅ FIRST define app
app = FastAPI(title="Payment Reconciliation System")

# ✅ STARTUP
@app.on_event("startup")
def startup():
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ DB connected & tables ready")
    except Exception as e:
        print("❌ DB connection failed:", e)

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
    try:
        result = db.execute(text("SELECT 1")).fetchone()
        return {"status": "connected", "result": str(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
        merchant = Merchant(id=event.merchant_id, name=event.merchant_name or "")
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

    # update status
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
# BULK INGESTION
# -----------------------------
@app.post("/events/bulk")
def ingest_bulk(events: List[EventCreate], db: Session = Depends(get_db)):

    processed = 0
    skipped = 0
    seen_event_ids = set()

    for event in events:

        if event.event_id in seen_event_ids:
            skipped += 1
            continue
        seen_event_ids.add(event.event_id)

        existing = db.query(Event).filter(Event.event_id == event.event_id).first()
        if existing:
            skipped += 1
            continue

        merchant = db.query(Merchant).filter(Merchant.id == event.merchant_id).first()
        if not merchant:
            merchant = Merchant(id=event.merchant_id, name=event.merchant_name or "")
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

        # update status
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
    return {"processed": processed, "skipped_duplicates": skipped}

# -----------------------------
# TRANSACTIONS (UPGRADED)
# -----------------------------
@app.get("/transactions")
def get_transactions(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)

    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    if status:
        query = query.filter(Transaction.status == status)

    if start_date:
        query = query.filter(Transaction.created_at >= datetime.fromisoformat(start_date))

    if end_date:
        query = query.filter(Transaction.created_at <= datetime.fromisoformat(end_date))

    query = query.order_by(Transaction.created_at.desc())

    offset = (page - 1) * limit
    txns = query.offset(offset).limit(limit).all()

    return txns

# -----------------------------
# SINGLE TRANSACTION (WITH EVENTS)
# -----------------------------
@app.get("/transactions/{txn_id}")
def get_transaction(txn_id: str, db: Session = Depends(get_db)):

    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()

    if not txn:
        return {"error": "Transaction not found"}

    events = db.query(Event)\
        .filter(Event.transaction_id == txn_id)\
        .order_by(Event.timestamp)\
        .all()

    return {
        "transaction": txn,
        "events": events
    }

# -----------------------------
# RECONCILIATION SUMMARY (GROUPED)
# -----------------------------
@app.get("/reconciliation/summary")
def get_summary(db: Session = Depends(get_db)):

    summary = db.query(
        Transaction.merchant_id,
        Transaction.status,
        func.count().label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).group_by(
        Transaction.merchant_id,
        Transaction.status
    ).all()

    return summary

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