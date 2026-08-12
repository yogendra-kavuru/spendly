# AI usage

AI coding assistance, including Codex/IDE assistance, was used during implementation for scaffolding and refinement, test-generation suggestions, debugging, reviewing alternatives, and documentation assistance. The resulting code, behavior, and documentation were reviewed and validated with the repository's tests and local application checks.

## Examples of reviewed AI-assisted work

### Duplicate transaction IDs

An initial straightforward design could have treated the source JSON `id` as a primary or unique identifier. Dataset inspection showed duplicate IDs representing separate records, so the design uses a generated database primary key and preserves the source value in non-unique `transaction_id`.

### Amount type inconsistency

Dataset inspection found numeric-string amounts as well as JSON numeric amounts. The parser converts values with `Decimal(str(value))` rather than floating-point conversion.

### Negative successful transactions

A naive reward calculation could award coins to every `SUCCESS` transaction. The source includes negative successful values, so the business rule was refined: only positive successful transactions earn coins and count toward positive-spending analytics.

### Month-input crash

Manual frontend testing found that partially editing a month value could create an invalid date and raise a `RangeError`. Month values are now validated as `YYYY-MM` before formatting or querying; incomplete input remains an editing value instead of an analytics value.

### Analytics UX

All-time category analytics were initially implemented. A large historical Grocery outlier made the all-time chart less useful, so the endpoint and UI were changed to use a selected calendar month. The source data remains unchanged.

## Verification

AI-assisted changes were checked with:

- Backend `pytest`
- Frontend lint and production build
- Manual API checks
- Browser/network and responsive UI checks
- Deterministic database reseeding
