# Spendly

Spendly is a full-stack consumer-finance dashboard for exploring transaction history, monthly spending analytics, reward coins, and reward redemption. It uses a Next.js + TypeScript frontend, a FastAPI backend, PostgreSQL, and approximately 10,000 supplied transaction records.

## Features

### Transactions

- Imports all 10,000 supplied transactions into PostgreSQL.
- Hand-built, semantic transaction table with server-side pagination.
- Debounced merchant search, category/status/date/amount filters, and date/amount sorting.
- Transaction details drawer using the already-loaded row data.

### Spending analytics

- Month-scoped category spending donut chart and category breakdown.
- Selecting a chart category filters the transaction table.
- Only positive `SUCCESS` transactions count as spending.

### Rewards

- Stored reward-wallet balance and active reward catalog.
- Affordability states and confirmation before redemption.
- Successful redemption updates the visible balance; insufficient balance is handled safely.
- PostgreSQL row locking prevents concurrent redemption requests from overspending a wallet.

### UX

- Responsive desktop and mobile layout.
- Loading, error, and empty states.
- Accessible controls and dialogs.
- Shared selected-month state and TanStack Query server-state synchronization.

## Tech stack

| Area | Technologies |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, TanStack Query, Recharts, lucide-react, CSS Modules/plain CSS |
| Backend | Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, psycopg, Pydantic, pydantic-settings, pytest |

## Architecture

```text
transactions.json
      ↓
normalization/parser
      ↓
PostgreSQL
      ↓
SQLAlchemy
      ↓
FastAPI
      ↓
Next.js / TanStack Query
      ↓
Dashboard UI
```

The parser normalizes irregular source values. The seed creates deterministic demo state. PostgreSQL stores application state, FastAPI performs filtering and aggregation, and the typed frontend API layer consumes those responses.

## Repository structure

```text
spendly/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── data/
│   │   ├── models/
│   │   └── schemas/
│   ├── alembic/
│   ├── data/
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── providers/
├── ASSUMPTIONS.md
├── DECISIONS.md
└── AI-USAGE.md
```

## Prerequisites

- PostgreSQL (running locally or otherwise reachable through `DATABASE_URL`)
- Python 3.13 is used by the current project environment
- Node.js 20.9.0 or later (required by the installed Next.js version)
- npm

Docker is not required or used for this project. PostgreSQL host, port, and credentials are configurable through environment variables.

## Database creation

Create a PostgreSQL database before running migrations. For example:

```bash
createdb spendly
```

Or use your preferred PostgreSQL administration tool:

```sql
CREATE DATABASE spendly;
```

## Backend setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` in `backend/.env` to your PostgreSQL database. For example:

```env
DATABASE_URL=postgresql+psycopg://localhost:5432/spendly
FRONTEND_ORIGIN=http://localhost:3000
```

The tracked `.env.example` currently uses port `5433`; change it to match your local PostgreSQL instance. That port is not required.

Apply the schema and seed deterministic demo data:

```bash
alembic upgrade head
python -m app.data.seed
```

Start the backend:

```bash
fastapi dev app/main.py
```

The API runs at `http://127.0.0.1:8000`; Swagger is available at `http://127.0.0.1:8000/docs`.

## Seed behavior

Run the deterministic seed from `backend/`:

```bash
python -m app.data.seed
```

It loads `data/transactions.json`, normalizes the source data, creates the Demo User, inserts all 10,000 transactions, inserts five rewards, creates one wallet, and resets redemptions. Re-running it restores the same logical demo state.

The available demo wallet balance is intentionally set to **1,500 coins**. It is controlled demo state—not the lifetime earned-coin total from the historical dataset—so both successful and insufficient-balance redemption paths can be demonstrated.

## Frontend setup

From the repository root:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The frontend environment variable is:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Open `http://localhost:3000`.

## Running both applications

Use two terminals after backend setup.

Terminal 1:

```bash
cd backend
source .venv/bin/activate
fastapi dev app/main.py
```

Terminal 2:

```bash
cd frontend
npm run dev
```

## API endpoints

### Health and local diagnostics

- `GET /health`
- `GET /db-check` — returns the connected database and PostgreSQL version.

### Transactions

- `GET /api/transactions`
  - `page`, `page_size`, `search`, `category`, `status`
  - `date_from`, `date_to`, `amount_min`, `amount_max`
  - `sort_by` (`date` or `amount`), `sort_order` (`asc` or `desc`)
- `GET /api/transactions/metadata`

### Analytics

- `GET /api/analytics/categories?month=YYYY-MM`

`month` is required.

### Rewards

- `GET /api/rewards`
- `GET /api/rewards/balance`
- `POST /api/rewards/{reward_id}/redeem`

## Reward rules

An eligible transaction has `status == SUCCESS` and `amount > 0`.

- One coin is earned for each full ₹100 spent.
- Each transaction earns at most 100 coins.
- `FAILED`, `PENDING`, and negative `SUCCESS` transactions earn zero coins.

The earning helper remains implemented and tested, even though the seeded available wallet balance is intentionally controlled at 1,500 coins.

## Analytics rules

Category analytics are scoped to a requested calendar month using Asia/Kolkata semantics. Only `SUCCESS` transactions with `amount > 0` count toward positive spending. Failed, pending, zero-value, and negative successful transactions are excluded.

## Data normalization

The supplied JSON includes ISO UTC and offset timestamps, date-only values, `DD/MM/YYYY HH:mm:ss` values, epoch milliseconds, numeric-string amounts, negative amounts, missing categories, lowercase statuses, and duplicate source IDs.

- Missing, null, and blank categories become `Uncategorized`.
- Statuses normalize to uppercase canonical values.
- Money uses Python `Decimal` and PostgreSQL `NUMERIC`.
- Source JSON `id` is stored as non-unique `transaction_id`.
- The database uses a separate generated primary key because source IDs can repeat.

See [ASSUMPTIONS.md](ASSUMPTIONS.md) and [DECISIONS.md](DECISIONS.md) for the rationale behind these rules.

## Tests and checks

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Known limitations

- The app uses one demo user; there is no authentication.
- Rewards are seeded catalog data, not admin-managed.
- There is no redemption-history UI.
- Transactions are read-only; no transaction creation or editing flow exists.
- Local setup requires PostgreSQL.
- Analytics focus on category spending for one selected month, not historical trend charts.
