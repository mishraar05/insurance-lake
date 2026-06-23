# Config Model Specifications (Decomposed)

This directory contains the decomposed configuration model specifications, organized by concern.

## File Structure

| Spec File | Purpose | Size Est. | Dependencies |
|-----------|---------|-----------|--------------|
| `config-model-core-spec.md` | Main orchestrator & architecture | ~500 lines | All others |
| `config-types-enums-spec.md` | Shared enums & exceptions | ~400 lines | None |
| `config-storage-spec.md` | EAV/PARAM storage & ConfigLoader | ~800 lines | config-types-enums |
| `source-target-spec.md` | SourceConfig & TargetConfig entities | ~3,000 lines | config-types-enums, config-storage |
| `load-config-spec.md` | LoadConfig entity | ~4,000 lines | All above |
| `transform-dq-spec.md` | TransformConfig & DQRuleConfig | ~2,500 lines | config-types-enums, config-storage, source-target |
| `config-validators-spec.md` | Comprehensive validation library | ~3,000 lines | All config specs |

## Generation Order

When regenerating code from these specs, follow this dependency order:

1. `config-types-enums-spec.md` → generates `config_types.py`
2. `config-storage-spec.md` → generates `config_loader_base.py`
3. `source-target-spec.md` → generates `source_config.py`, `target_config.py`
4. `load-config-spec.md` → generates `load_config.py`
5. `transform-dq-spec.md` → generates `transform_config.py`, `dq_config.py`
6. `config-validators-spec.md` → generates `validators.py`
7. `config-model-core-spec.md` → generates integration code & tests

## Original Spec

The original monolithic spec is preserved at:
- `../config-model-spec.md` (34,355 lines, archived)

## Status

- **Created:** 2026-06-23
- **Decomposition:** 7 modular specs (saving ~20K lines via deduplication)
- **Maintainer:** EY InsureLake Team
