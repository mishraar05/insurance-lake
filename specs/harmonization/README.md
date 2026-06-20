# Harmonization Specs (HARM)

Data transformation and ACORD canonical model alignment.

## Specs in this folder

### 📋 Planned
- **harmonization-engine-spec.md** (HARM-001, HARM-002) - Main harmonization engine
- **acord-mapping-spec.md** (HARM-020, HARM-021) - ACORD canonical mapping
- **transformation-patterns-spec.md** (HARM-030, HARM-031) - Transform patterns
- **silver-gold-spec.md** (HARM-050, HARM-051, HARM-054) - Medallion layers

## Key Features
- SQL and Python transformations
- ACORD canonical model alignment (Party, Policy, Coverage, Claim, Payment, Loss)
- SCD1/SCD2 transforms
- Declarative (Lakeflow) + non-declarative (classic batch PySpark)
- Column-level lineage
- Data standardization UDFs

## Backlog Tasks
- HARM-001: Harmonization framework design
- HARM-002: Config-driven transforms
- HARM-010: SQL transformation engine
- HARM-020: Source-to-target mapping
- HARM-021: ACORD canonical model
- HARM-030: SCD1 transforms
- HARM-031: SCD2 transforms
- HARM-040: Workflow orchestration
- HARM-050: Silver layer design
- HARM-051: Gold layer design
- HARM-054: Business aggregations
