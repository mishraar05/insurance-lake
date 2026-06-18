# Data Masking Specs (MASK)

PII/PHI classification and masking techniques.

## Specs in this folder

### 📋 Planned
- **masking-engine-spec.md** (MASK-001, MASK-002) - Masking engine
- **pii-classification-spec.md** (MASK-010) - PII/PHI detection
- **masking-techniques-spec.md** (MASK-020, MASK-021) - Masking methods

## Key Features
- PII/PHI column classification (auto-detection)
- Dynamic masking (Unity Catalog row filters, column masks)
- Physical masking (tokenization, hashing, redaction)
- Masking policy management
- Compliance reporting (GDPR, HIPAA)

## Backlog Tasks
- MASK-001: Masking framework design
- MASK-002: Config-driven masking
- MASK-010: PII classification
- MASK-020: Dynamic masking (UC)
- MASK-021: Physical masking

## Note
⚠️ **Paid edition only** - requires Model Serving for PII classification
