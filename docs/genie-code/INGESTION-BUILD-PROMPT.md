# Ingestion framework - Genie Code build (bottom-up, gap-gated)

**Do NOT ask Genie Code to "build the ingestion framework" in one shot** - it wanders. Build one component at a time, in dependency order, each gated by the spec-gap protocol (Phase 1 gaps -> enrich -> Phase 2 generate -> run acceptance -> next). Genie Code on **Ask-first**; skill `insurelake-spec-codegen` installed.

## Build order (dependency closure of `ingestion.engine`)
| # | spec | target_path |
|---|------|-------------|
| 1 | specs/foundation/contracts-spec.md       | src/core/contracts/ |
| 2 | specs/foundation/config-model-spec.md     | src/core/metadata/ |
| 3 | specs/foundation/abc-sdk-spec.md          | src/core/sdk/  (fix §6 lint first - Phase 1 will flag it) |
| 4 | specs/dataio/file-readers-spec.md         | src/dataio/readers/file/ |
| 5 | specs/dataio/append-strategy-spec.md      | src/dataio/load_strategy/append/ |
| 6 | specs/dataio/schema-evolution-spec.md     | src/dataio/schema_evolution/ |
| 7 | specs/dataio/quarantine-spec.md           | src/dataio/quarantine/ |
| 8 | specs/ingestion/ingestion-engine-spec.md  | src/framework/ingestion/ |

The three foundation specs (1-3) are mutually near-foundational - build them first in any order; everything else depends on them. The engine (8) is last (it orchestrates 1-7).

## Kickoff prompt (paste into Genie Code)
---
Use the `insurelake-spec-codegen` skill. We are building the INGESTION framework from its specs, ONE component at a time, strictly bottom-up. The spec is the ONLY source of truth - never invent; if any needed detail is missing, output a `## SPEC GAPS` list and STOP.

Build order (do them in this exact sequence, one at a time):
1. specs/foundation/contracts-spec.md       -> src/core/contracts/
2. specs/foundation/config-model-spec.md     -> src/core/metadata/
3. specs/foundation/abc-sdk-spec.md          -> src/core/sdk/
4. specs/dataio/file-readers-spec.md         -> src/dataio/readers/file/
5. specs/dataio/append-strategy-spec.md      -> src/dataio/load_strategy/append/
6. specs/dataio/schema-evolution-spec.md     -> src/dataio/schema_evolution/
7. specs/dataio/quarantine-spec.md           -> src/dataio/quarantine/
8. specs/ingestion/ingestion-engine-spec.md  -> src/framework/ingestion/

For EACH component, and PAUSE for my approval between phases:
- Phase 1 (no code): read the spec end-to-end; output its `## SPEC GAPS` (each = §ref + what's missing + the one question), or `NO GAPS - ready to generate`. Then STOP.
- Phase 2 (only after I say "go"): emit the §3 interface VERBATIM; implement §6 literally (Procedure, Decision rules, Key code fragments, every Edge case); write code ONLY to the spec's target_path and the §9 tests to the mirrored tests/ path; obey the §6 hard constraints; add no dependency the spec doesn't name; no TODOs/placeholders. If you hit a new gap, STOP and report it - do not invent.
- Then run the spec's `acceptance:` commands and show the output. STOP for my OK before moving to the next component.

Start with component 1 (core.contracts), Phase 1 only.
---

## After each component
- Run that spec's own `acceptance:` commands (the deterministic proof it followed the spec).
- Diff the generated public signatures vs the spec's §3 (must match).
- Only then move to the next component.
