# 🧠 Payment Reconciliation System

## Overview

This project implements an event-driven payment reconciliation system that ingests transaction events and maintains a consistent transaction state across its lifecycle.

Instead of directly updating transactions, the system processes events such as:

- `payment_initiated`
- `payment_processed`
- `payment_failed`
- `settled`

The current transaction state is derived from these events.

---

## 🚀 Live API

**Live URL:** [https://payments-system-dzt9.onrender.com](https://payments-system-dzt9.onrender.com)

**Swagger Docs:** `/docs`

---

## ⚙️ Tech Stack

- **FastAPI** (API layer)
- **PostgreSQL / Supabase** (Database)
- **SQLAlchemy** (ORM)
- **Render** (Deployment)

---

## 🧩 System Design

### Event-Driven Architecture
- All updates are ingested as events.
- Transactions evolve based on the event sequence.
- Ensures full auditability and traceability.

### Idempotency
- Duplicate events are prevented using `event_id`.
- Ensures safe retries in distributed systems.

### Bulk Ingestion
- Supports batch processing.
- In-memory deduplication + DB-level validation.
- Reduces redundant database operations.

### Data Model
- **Merchants**
- **Transactions**
- **Events** (The single source of truth)

### Indexing Strategy
Indexes added on:
- `event_id` (Idempotency)
- `transaction_id` (Event lookup)
- `merchant_id`, `status` (Filtering)
- `created_at`, `timestamp` (Range queries)

---

## 📊 APIs

### Event Ingestion
- `POST /events`
- `POST /events/bulk`

### Transactions
- `GET /transactions`
  - Supports filtering by:
    - `merchant_id`
    - `status`
    - `date range`
  - Pagination included.
- `GET /transactions/{id}`
  - Includes full event history.

### Reconciliation
- `GET /reconciliation/summary`
  - Grouped by merchant & status.
- `GET /reconciliation/discrepensies`
  - Detects stuck transactions.

---

## 🧪 Testing

All endpoints were tested via Swagger UI.

**Tested scenarios:**
- Event lifecycle (`initiated` → `processed` → `settled`)
- Duplicate event handling
- Bulk ingestion
- Filtering + pagination
- Event history retrieval
- Reconciliation logic

---

## 🚀 Future Improvements

- Add strict event ordering guarantees.
- Introduce a message queue for massive scalability.
- Add robust retry mechanisms.
- Implement Alembic migrations.