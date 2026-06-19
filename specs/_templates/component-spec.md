---
# Machine-readable front-matter — the registry, router, and generator consume this.
id: <domain>.<component>                 # e.g. dataio.readers
title: <Component Title>
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

## 6. Implementation guidance + constraints
Path + pattern (Genie-Code-ready). Hard constraints: no new deps unless listed; no `Any` in public signatures; one module per concern; no network/IO unless required.

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
