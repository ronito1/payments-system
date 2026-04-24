# Payment Reconciliation System

## Overview

This project implements an **event-driven payment reconciliation system** where transaction state is derived from incoming events rather than direct updates.

Each payment goes through a lifecycle (initiated → processed → settled/failed), and all state changes are recorded as immutable events. This ensures **auditability, idempotency, and consistency** across the system.

The system supports bulk ingestion, transaction querying, event tracking, and reconciliation reporting.

---

## Architecture

* **Backend:** FastAPI (Python)
* **Database:** PostgreSQL (Supabase)
* **ORM:** SQLAlchemy
* **Deployment:** Render

## Design Decisions & Tradeoffs

- Used event-driven model to ensure auditability and traceability
- Chose PostgreSQL for strong relational integrity and aggregation queries
- Implemented idempotency using event_id checks to prevent duplicate processing
- Used synchronous processing for simplicity; async queues can be added for scale
- Prioritized SQL-based aggregation over application logic for performance
---

### Note

A live deployment is provided, so setting up a database locally is optional for evaluation.


## Environment Variables

Create a `.env` file and add:

DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
---

## Database Schema

### Merchants

* `id` (PK)
* `name`

### Transactions

* `id` (PK)
* `merchant_id` (FK)
* `amount`
* `currency`
* `status`
* `created_at`
* `updated_at`

### Events

* `event_id` (PK, UNIQUE)
* `event_type`
* `transaction_id` (FK)
* `merchant_id` (FK)
* `amount`
* `currency`
* `timestamp`
* `raw_payload`

### Indexing

* Indexed fields:

  * `transactions.status`
  * `transactions.merchant_id`
  * `events.event_type`
  * `events.event_id (unique)`

These indexes support efficient filtering, aggregation, and reconciliation queries.

---

## Features

### 1. Event Ingestion

* Create single events (`POST /events`)
* Bulk ingestion (`POST /events/bulk`)
* Duplicate detection using `event_id`

### 2. Transaction Management

* Retrieve all transactions with filters:

  * merchant_id
  * status
  * date range
* Pagination support

### 3. Event History

* Retrieve full event history per transaction
* Ordered chronologically for traceability

### 4. Reconciliation

* Summary endpoint:

  * Aggregates transactions by merchant & status
* Discrepancy detection:

  * Identifies stuck or inconsistent transactions

---

## API Endpoints

### Events

* `POST /events`
* `POST /events/bulk`

### Transactions

* `GET /transactions`
* `GET /transactions/{txn_id}`

### Reconciliation

* `GET /reconciliation/summary`
* `GET /reconciliation/discrepancies`

---
## Live API

Base URL:
https://payments-system-dzt9.onrender.com

Swagger Docs: --> where you can test the API
https://payments-system-dzt9.onrender.com/docs

Health Check:
https://payments-system-dzt9.onrender.com/test-db
---

## Setup Instructions (Local)

```bash
git clone <repo_url>
cd solutions-engineer

python -m venv venv
source venv/bin/activate   # (Mac/Linux)
venv\Scripts\activate      # (Windows)

pip install -r requirements.txt
```

Create `.env`:

```env
DATABASE_URL=your_database_url
```

Run server:

```bash
uvicorn main:app --reload
```

---

## Postman Collection

A Postman collection is included:

```
postman_collection.json
```

Import into Postman and run requests to test all APIs.

---

## Data & Testing

The system is designed and tested to handle large-scale event ingestion.

### Dataset Characteristics

* Supports **10,000+ events across multiple merchants (3+)**
* Includes a realistic mix of:

  * successful transactions (initiated → processed → settled)
  * failed transactions
  * duplicate events (same `event_id`)
  * inconsistent or unreconciled states (e.g., stuck in initiated/processed)

### Testing Approach

* Bulk ingestion endpoint (`/events/bulk`) was used to simulate high-volume event processing
* Duplicate handling was verified via:

  * repeated event submissions
  * batch-level deduplication
* Reconciliation endpoints were validated to:

  * correctly aggregate transaction states
  * identify incomplete or inconsistent transactions

### Note

Due to deployment constraints, full dataset ingestion is not persisted in the live environment, but the system is designed to handle such scale efficiently through:

* indexed queries
* database-level aggregation
* idempotent event processing
---

## Idempotency Handling

* Enforced via **unique constraint on `event_id`**
* Duplicate events are:

  * ignored at DB level
  * safely skipped during bulk ingestion

This ensures no duplicate transaction updates or corruption.

---

## Assumptions & Tradeoffs

* Event ordering is assumed to be mostly sequential
* Out-of-order events are handled but not strictly enforced
* Synchronous processing used for simplicity
* No message queue (e.g., Kafka/SQS) used — would be added for scale
* Focused on correctness and clarity over distributed system complexity

---

## Future Improvements

* Introduce async processing with queue (Kafka/SQS)
* Add retry & dead-letter queue for failed events
* Stronger state machine for transaction lifecycle
* Caching layer for high-frequency queries
* Monitoring & alerting for discrepancies

---

## Notes

This implementation prioritizes:

* correctness
* simplicity
* clarity of system behavior

over unnecessary complexity.

---
