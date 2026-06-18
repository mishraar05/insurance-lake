---
id: domain.pc-acord-canonical
name: pc-acord-canonical
category: domain
version: 0.1.0
maturity: draft
status: active
owner_role: Architect
runtime: agent-bricks
fe_ready: true
build_order: 0
depends_on: []
backlog_ids: ['HARM-021']
inputs: ['entity_request']
outputs: ['canonical_definitions']
tools: ['unity-catalog']
---

# P&C ACORD Canonical Knowledge

> Authoritative P&C / ACORD canonical model knowledge (party, policy, coverage, claim, payment, loss) used by build and authoring skills.

## Purpose / when to use
The authoritative P&C / ACORD canonical-model knowledge that build and authoring skills consult when mapping sources to silver and conforming to the canonical schema. Read-only knowledge; it does not process data.

## Inputs (contract)
- `entity_request` - a canonical entity and/or a source entity to map.
- `source_schema` - optional source columns to map.

## Procedure (Genie-Code-ready steps)
1. Resolve the requested canonical entity (Party, Policy, Coverage, Claim, Payment, Loss).
2. Return its key attributes, natural/surrogate keys, and relationships.
3. If a source schema is supplied, propose source -> canonical attribute mappings and flag PII/PHI.
4. State ACORD alignment + silver-layer naming conventions.

## Outputs (contract)
- `canonical_definitions` - entity, attributes, keys, relationships, source mappings, PII flags.

## Canonical entities (reference)
| Entity | Key attributes | Keys | Relationships |
|---|---|---|---|
| Party | party_id, party_type (Insured/Claimant/Agent/Beneficiary), name*, dob*, tax_id*, address*, contact* | party_id (SK) | insured on Policy; claimant on Claim |
| Policy | policy_id, policy_number, product, term_effective, term_expiry, status, issuing_party_id | policy_id (SK), policy_number (NK) | held by Party; has Coverages |
| Coverage | coverage_id, policy_id, coverage_code, limit_amount, deductible, premium | coverage_id (SK) | belongs to Policy; referenced by Claim |
| Claim | claim_id, claim_number, policy_id, coverage_id, loss_id, fnol_date, status, claimant_party_id | claim_id (SK), claim_number (NK) | on Policy/Coverage; has Payments; tied to Loss |
| Payment | payment_id, claim_id, policy_id, payment_type (Premium/Indemnity/Expense), amount, currency, paid_date | payment_id (SK) | indemnity on Claim; premium on Policy |
| Loss | loss_id, event_date, peril, cause, loss_location/geo, catastrophe_code | loss_id (SK) | drives Claims |

(* = PII/PHI - must be classified and masked.)

## Guardrails & policy
- ACORD-aligned naming; snake_case in silver; PII attributes (name, dob, tax_id, address, medical) always flagged for masking.

## Govern hooks
- Consumed by [[authoring.source-target-mapping]], [[authoring.metadata-population]], [[framework-dev.build-harmonization-engine]]; read-only knowledge.

## Examples
- Guidewire PolicyCenter `pc_policy` -> canonical `Policy` (policy_number, term dates, status); `pc_contact` -> `Party` (PII flagged).

## Acceptance / eval
- For a sample source schema, returns the correct canonical entity + mappings + PII flags matching the reference table.

## References
- Backlog: HARM-021
- Shared: ../../_shared/glossary.md
