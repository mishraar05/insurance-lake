---
# Machine-readable front-matter — the registry, router, and generator consume this.
id: <domain>.<component>                 # e.g. dataio.load-strategy
title: <Component Title>
owner: EY
status: draft|active|implemented
contracts_version: <x.y.z>               # only if it defines/depends on a versioned contract
target_path: src/<tier>/<component>/     # EXACT path the generator writes to
owning_skill: <skill that builds it>
backlog: [<TASK-IDs>]
provides: [<public classes/functions exposed>]
depends_on: [<other spec ids>]
generation_context:                      # the ONLY files the generator should read (bounds context)
  - <path/glob>
acceptance:                              # executable commands; ALL must pass = Definition of Done
  - "<command>"
regeneration: fully-generated|scaffold-then-edit   # may the generator overwrite this component?
capability:                               # OPTIONAL - only on user-selectable FEATURE specs (spec-per-feature)
  framework: <ingestion|harmonization|...>   # menu group the feature belongs to
  feature: <batch|streaming|scd2|...>        # the selectable leaf label
  selectable: true                           # appears in the capability menu
---

# <Component Title> - Specification

## 1. Purpose & scope
What it solves; in-scope / out-of-scope.

## 2. Requirements
Functional (FR-n) + Non-functional (NFR-n). Specific and testable.

## 3. Interface - exact skeleton (the generator MUST emit this)
```<language>
<the literal signatures / class stubs the generated code must match>
```
Net-new: full stub. Already-built: the current signatures.

## 4. Inputs / Outputs
Config models consumed; data produced; side effects.

## 5. Design
Key decisions, components, data flow; declarative vs imperative where relevant; which `core/contracts` interface it implements.

## 6. Implementation logic & guidance
**Logic / algorithm** — REQUIRED for logic modules (only "N/A" for pure interface/data modules such as contracts/metadata). This is the source of truth for the logic; the generator translates it, it does not invent it:
- **Procedure:** numbered, deterministic steps the code performs.
- **Decision rules:** branching/selection (e.g. `load_pattern x engine -> strategy`).
- **Key code fragments:** the literal critical snippets the generated code MUST contain (e.g. the `MERGE` statement, `dlt.create_auto_cdc_flow(...)`, `cloudFiles` options, a regex).
- **Edge cases:** late-arriving data, deletes, schema drift, empty input, idempotency/restart.

**Guidance:** target path; Genie-Code-ready notes; idiomatic patterns to follow.
**Constraints (hard):** no new deps unless listed; no `Any` in public signatures; one module per concern; no network/IO unless required; instrument via the ABC SDK + structured logging.

## 7. Validation, edge cases & versioning policy
Edge cases; breaking-change policy; how signatures are enforced (mypy).

## 8. Error handling + ABC instrumentation
Failure modes; MUST call the ABC SDK (audit/balance/cost) + structured logging.

## 9. Testing & acceptance
Point to front-matter `acceptance`. Unit (mock Spark) + integration (real Spark) where needed; >80% coverage.

## 10. Examples
>=1 conformant example per public interface + at least one counter-example (what NOT to do).

## 11. Regeneration contract
`fully-generated` (safe to overwrite) or `scaffold-then-edit` (generate skeleton; humans complete marked sections).

## 12. References
Dependent specs, contracts, standards.
