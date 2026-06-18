# Data Quality & Reconciliation Specs (DQ, REC)

Data quality rules and financial reconciliation.

## Specs in this folder

### 📋 Planned
- **dq-engine-spec.md** (DQ-001, DQ-002) - Data quality engine
- **dq-rules-catalog-spec.md** (DQ-010, DQ-011) - Standard rules catalog
- **reconciliation-engine-spec.md** (REC-001, REC-002) - Recon engine
- **recon-patterns-spec.md** (REC-010, REC-011, REC-020) - Recon patterns

## Key Features

### Data Quality
- At-rest (batch) and in-motion (streaming) checks
- Rule types: NOT_NULL, UNIQUE, RANGE, REGEX, REFERENTIAL, CUSTOM_SQL
- Actions: WARN, FAIL, QUARANTINE
- Threshold-based validation
- DQ dashboard and alerting

### Reconciliation
- Count reconciliation (row counts across layers)
- Financial control-total reconciliation
- Variance detection and alerting
- Feeds ABC Balance table

## Backlog Tasks
- DQ-001: DQ framework design
- DQ-002: Config-driven DQ
- DQ-010: Rule engine implementation
- DQ-011: Quarantine logic
- DQ-030: DQ monitoring
- DQ-040: DQ alerting
- REC-001: Recon framework design
- REC-002: Config-driven recon
- REC-010: Count recon
- REC-011: Financial recon
- REC-020: Variance detection
