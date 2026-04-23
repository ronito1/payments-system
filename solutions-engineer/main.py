from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime
from typing import List, Optional

from app import models
from app.db import engine, get_db
from app.models import Event, Transaction, Merchant
from app.schemas import (
    EventCreate,
    Transaction as TransactionSchema,
    Event as EventSchema
)

# -----------------------------
# APP INIT
# -----------------------------
app = FastAPI(title="Payment Reconciliation System")


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
    """Health check endpoint to verify API is running."""
    return {"message": "Payment Reconciliation API", "docs": "https://payments-system-dzt9.onrender.com/docs", "health_check": "/test-db"}


# -----------------------------
# DB TEST
# -----------------------------
@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    """Simple endpoint to test database connectivity."""
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
    """
    Ingests a single transaction event.
    Updates the transaction state based on the event type.
    """

    # Idempotency check
    existing = db.query(Event).filter(Event.event_id == event.event_id).first()
    if existing:
        return {
            "message": "Duplicate event ignored",
            "event_id": event.event_id,
            "transaction_id": event.transaction_id
        }

    # Ensure merchant exists
    merchant = db.query(Merchant).filter(Merchant.id == event.merchant_id).first()
    if not merchant:
        merchant = Merchant(id=event.merchant_id, name=event.merchant_name or "")
        db.add(merchant)

    # Ensure transaction exists
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

    # Insert event
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

    # Status updates
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

    # 🔥 Status-specific response
    status_messages = {
        "payment_initiated": "Payment initiated successfully",
        "payment_processed": "Payment processed successfully",
        "payment_failed": "Payment failed",
        "settled": "Payment settled successfully"
    }

    return {
        "message": status_messages.get(event.event_type, "Event processed successfully"),
        "event_id": event.event_id,
        "transaction_id": event.transaction_id
    }


# -----------------------------
# BULK INGESTION
# -----------------------------
@app.post("/events/bulk")
def ingest_bulk(events: List[EventCreate], db: Session = Depends(get_db)):
    """
    Ingests multiple transaction events in bulk.
    Handles deduplication and bulk transaction state updates.
    """

    processed = 0
    skipped = 0
    seen_event_ids = set()

    for event in events:

        # Skip duplicates inside the same batch
        if event.event_id in seen_event_ids:
            skipped += 1
            continue
        seen_event_ids.add(event.event_id)

        # Check if event already exists in the database
        existing = db.query(Event).filter(Event.event_id == event.event_id).first()
        if existing:
            skipped += 1
            continue

        # Ensure merchant exists
        merchant = db.query(Merchant).filter(Merchant.id == event.merchant_id).first()
        if not merchant:
            merchant = Merchant(id=event.merchant_id, name=event.merchant_name or "")
            db.add(merchant)

        # Ensure transaction exists
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

        # Insert event
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

        # Status update
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
        "skipped_duplicates": skipped,
        "message": "Bulk events processed successfully"
    }


# -----------------------------
# TRANSACTIONS (FILTERED + PAGINATED)
# -----------------------------
@app.get("/transactions", response_model=List[TransactionSchema])
def get_transactions(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Retrieves transactions with optional filtering and pagination.
    """
    # Base query
    query = db.query(Transaction)

    # Apply filters if provided
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    if status:
        query = query.filter(Transaction.status == status)

    if start_date:
        query = query.filter(Transaction.created_at >= datetime.fromisoformat(start_date))

    if end_date:
        query = query.filter(Transaction.created_at <= datetime.fromisoformat(end_date))

    # Sort by latest first
    query = query.order_by(Transaction.created_at.desc())

    # Apply pagination
    offset = (page - 1) * limit
    txns = query.offset(offset).limit(limit).all()

    return txns


# -----------------------------
# SINGLE TRANSACTION (WITH EVENTS)
# -----------------------------
@app.get("/transactions/{txn_id}")
def get_transaction(txn_id: str, db: Session = Depends(get_db)):
    """
    Retrieves a single transaction and its entire event history.
    """
    # Fetch the transaction
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()

    if not txn:
        return {"error": "Transaction not found"}

    # Fetch all related events sorted by timestamp
    events = db.query(Event)\
        .filter(Event.transaction_id == txn_id)\
        .order_by(Event.timestamp)\
        .all()

    return {
        "transaction": TransactionSchema.model_validate(txn),
        "events": [EventSchema.model_validate(e) for e in events]
    }


# -----------------------------
# RECONCILIATION SUMMARY
# -----------------------------
@app.get("/reconciliation/summary")
def get_summary(db: Session = Depends(get_db)):
    """
    Generates a reconciliation summary grouped by merchant and transaction status.
    """
    # Aggregate transactions by merchant and status
    results = db.query(
        Transaction.merchant_id,
        Transaction.status,
        func.count().label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).group_by(
        Transaction.merchant_id,
        Transaction.status
    ).all()

    return [
        {
            "merchant_id": r.merchant_id,
            "status": r.status,
            "count": r.count,
            "total_amount": float(r.total_amount or 0)
        }
        for r in results
    ]


# -----------------------------
# DISCREPANCIES
# -----------------------------
@app.get("/reconciliation/discrepancies")
def get_discrepancies(db: Session = Depends(get_db)):
    """
    Identifies problematic transactions stuck in intermediate states.
    """
    # Find transactions that are stuck in 'initiated' state
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