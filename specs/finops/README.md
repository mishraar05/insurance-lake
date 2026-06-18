# FinOps Specs (FINOPS)

Cost tracking, estimation, and optimization.

## Specs in this folder

### 📋 Planned
- **cost-tracking-spec.md** (FINOPS-001, FINOPS-002) - Cost tracking
- **cost-estimation-spec.md** (FINOPS-010) - Customer cost estimation
- **finops-dashboard-spec.md** (FINOPS-020) - Cost dashboard

## Key Features
- Consumption tracking (DBU, SQL warehouse time, Genie Code)
- Cost attribution (per feed, per transform, per pipeline)
- Customer cost estimation (Free Edition benchmark → Paid projection)
- Cost optimization recommendations
- Budget alerts
- FinOps dashboard

## Methodology
1. Measure consumption on Free Edition
2. Derive unit costs (per feed/transform/generation)
3. Apply paid list prices
4. Scale by customer volume
5. Generate low/expected/high cost bands

## Backlog Tasks
- FINOPS-001: Cost tracking framework
- FINOPS-002: Cost attribution
- FINOPS-010: Cost estimation model
- FINOPS-020: FinOps dashboard
