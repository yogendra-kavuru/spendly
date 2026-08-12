# Technical decisions

## Internal database ID and `transaction_id`

The supplied source IDs are duplicated for distinct rows. Spendly therefore uses a generated `BIGINT` primary key for internal identity and stores the source value in a non-unique `transaction_id` column. This preserves every record.

## PostgreSQL `NUMERIC` and Python `Decimal`

Money is stored as PostgreSQL `NUMERIC` and handled as Python `Decimal`, avoiding floating-point precision errors for transaction and reward values.

## Normalize at ingestion

The parser normalizes dirty source formats once at the parser/seed boundary. Downstream database, API, and UI layers receive consistent timestamps, categories, statuses, and monetary values.

## Server-side transaction querying

The browser does not load all 10,000 transactions. PostgreSQL performs filtering, sorting, and pagination; the API limits requested pages to 100 rows, with a default page size of 50.

## PostgreSQL aggregation for analytics

Category `SUM` and `COUNT` use database-side `GROUP BY` queries instead of aggregating transaction rows in Python or the browser.

## Monthly category analytics

Category spending is scoped to a selected month. This is more useful than all-time totals when a large historical Grocery transaction would dominate a chart. No source transaction is removed, capped, or altered.

## TanStack Query with local UI state

TanStack Query manages server data, caching, mutations, and cache updates. Component state is sufficient for filters, selected month, selected category, and dialogs, so Redux would add unnecessary complexity.

## Hand-built transaction table

The transaction table uses semantic HTML and CSS rather than a table/grid library, matching the assignment's requirement to implement table behavior directly.

## Native month and date inputs

Native controls provide accessible, responsive date selection with less custom UI. Strict `YYYY-MM` validation prevents incomplete values from reaching date formatting or analytics requests.

## Pessimistic reward redemption UI

The frontend waits for a successful redemption response before changing the displayed wallet balance. This avoids optimistic-update rollback complexity and leaves the backend authoritative.

## `SELECT FOR UPDATE` during redemption

The backend locks the wallet row before checking and deducting balance. This prevents concurrent redemption requests from observing the same balance and overspending it.

## Seeded reward catalog

Reward definitions are deterministic seed data. Reward-administration CRUD would not add value to this take-home.

## No Docker

Local development uses PostgreSQL directly. Docker is intentionally not part of the project setup.
