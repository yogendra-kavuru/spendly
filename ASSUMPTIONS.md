# Assumptions

## 1. Demo user

Spendly represents one Demo User. Authentication and multi-user behavior are outside this take-home's scope.

## 2. Wallet balance

The transaction file represents historical activity. The deterministic demo wallet is initialized to **1,500 coins** so an evaluator can demonstrate both successful and insufficient-balance redemptions. This is intentional controlled demo state; it is not derived from the historical transaction total. The historical coin-earning formula remains implemented and tested.

## 3. Reward earning

- Only positive `SUCCESS` transactions earn coins.
- One coin is awarded for each full ₹100.
- A transaction earns at most 100 coins.
- `FAILED`, `PENDING`, and negative `SUCCESS` transactions earn zero coins.

## 4. Negative amounts

Negative successful transactions are treated as refund/reversal-like records. Their status and amount are preserved, but they do not earn coins and do not contribute to positive-spending analytics.

## 5. Categories

Missing, null, and blank categories normalize to `Uncategorized`.

## 6. Timestamp semantics

- Explicit ISO timezone values retain their represented instant.
- Epoch values represent Unix epoch milliseconds.
- Date-only and `DD/MM/YYYY HH:mm:ss` values are interpreted in Asia/Kolkata.

## 7. Analytics

Spending analytics are scoped to the selected calendar month and count only positive `SUCCESS` transactions.

## 8. Amount filters

Amount filter boundaries are inclusive. Negative values remain valid because the source contains negative transactions.

## 9. Redemption

Redemption is final for this take-home. Cancellation or refund of a redeemed reward is not implemented.
