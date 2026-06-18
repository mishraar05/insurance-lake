# Ingestion Specs (ING)

Batch and streaming data ingestion patterns.

## Specs in this folder

### 📋 Planned
- **ingestion-engine-spec.md** (ING-001, ING-002) - Main ingestion engine
- **autoloader-patterns-spec.md** (ING-010, ING-012) - Auto Loader implementation
- **streaming-patterns-spec.md** (ING-020, ING-030) - Streaming patterns
- **scd-patterns-spec.md** (ING-031, ING-052) - SCD1/SCD2 patterns

## Key Features
- Auto Loader for cloud files (S3, ADLS, GCS)
- Batch full, batch incremental, streaming append
- SCD1 (overwrite), SCD2 (history tracking)
- Checkpoint management
- Schema evolution
- Data arrival monitoring

## Backlog Tasks
- ING-001: Ingestion framework design
- ING-002: Config-driven ingestion
- ING-010: Auto Loader implementation
- ING-012: Schema inference
- ING-020: Streaming append
- ING-030: Checkpoint management
- ING-031: SCD2 ingestion
- ING-041: Synthetic data generation
- ING-050: Anomaly detection on ingestion
- ING-052: CDC support
