---
id: agentic.capability-registry
title: Capability Registry & Resolver
owner: EY
status: active
target_path: src/agents/registry/
owning_skill: orchestration.router
backlog: [AGENT-003]
provides: [Capability, load_registry, menu, resolve_selection, build_plan]
depends_on: []
generation_context:
  - specs/**/*.md                      # reads every spec's front-matter
  - specs/_templates/component-spec.md
acceptance:
  - "pytest tests/agents/test_registry.py"
  - "python -c 'from agents.registry import load_registry, menu, build_plan'"
regeneration: scaffold-then-edit       # menu DATA is derived from specs; resolver is code
---

# Capability Registry & Resolver - Specification

## 1. Purpose & scope
Turn the framework's capabilities into a **selectable menu** and turn a selection into a **build plan**. This is the engine behind the engagement model: *Which frameworks? -> Which features?*, where **every selectable feature is tagged to exactly one spec (spec-per-feature)**. Selecting a feature pulls that spec (+ its dependencies); skills + Genie Code then build from it (control plane only).
- In scope: the capability tree (built from spec front-matter), the menu, and the resolver that produces a dependency-ordered build plan.
- Out of scope: the chat surface (separate spec), the actual code generation (router + Genie + framework-dev/authoring skills).

## 2. Requirements
**Functional**
- FR-1: Build a registry by scanning every spec's `capability` + `depends_on` front-matter.
- FR-2: A spec is a selectable feature iff `capability.selectable: true`; group features by `capability.framework`.
- FR-3: `menu()` returns `framework -> [features]` for the UI/chat.
- FR-4: `resolve_selection(spec_ids)` returns the selected ids plus their transitive `depends_on` closure.
- FR-5: `build_plan(spec_ids)` returns a **topologically ordered** list of steps; each step = `{spec_id, target_path, acceptance, depends_on}`.
- FR-6: Enforce **spec-per-feature** - each `(framework, feature)` maps to exactly one spec id.

**Non-functional**: deterministic; the menu is **derived from the specs** (single source of truth - no separately hand-maintained menu that can drift).

## 3. Interface - exact skeleton (the generator MUST emit this)
```python
@dataclass
class Capability:
    framework: str
    feature: str
    spec_id: str
    selectable: bool

def load_registry(specs_dir: Path) -> list[Capability]: ...     # scan front-matter
def menu(reg: list[Capability]) -> dict[str, list[str]]: ...    # framework -> [features]
def resolve_selection(spec_ids: list[str], specs_dir: Path) -> list[str]: ...  # + depends_on closure
def build_plan(spec_ids: list[str], specs_dir: Path) -> list[dict]: ...        # ordered steps
```

## 4. Inputs / Outputs
- Input: the `specs/` tree (front-matter of every spec).
- Output: a `menu` (for the chat/UI) and a `build_plan` (for `orchestration.router` to execute via Genie Code).

## 5. Design
The registry is **generated from spec front-matter** - no parallel menu file. The resolver is a topological sort over `depends_on`. Spec-per-feature is validated at load time. The build plan is what the router consumes to drive generation, gating each step.

## 6. Implementation logic & guidance
**Logic / algorithm** (source of truth):
- **Procedure:**
  1. Walk `specs/**/*.md`; parse YAML front-matter (`id`, `capability`, `depends_on`, `target_path`, `acceptance`).
  2. For each spec with `capability.selectable: true`, record `Capability(framework, feature, id, True)`.
  3. `menu()` = group capabilities by `framework` -> sorted feature labels.
  4. `resolve_selection(selected)` = compute closure: start with `selected`; repeatedly add each spec's `depends_on` until fixed point.
  5. `build_plan(selected)` = topologically sort the closure by `depends_on`; emit `{spec_id, target_path, acceptance, depends_on}` per node, foundation-first.
  6. Validate: every `capability.spec_id` resolves to a real spec; each `(framework, feature)` is unique (spec-per-feature); no `depends_on` cycles.
- **Decision rules:** selectable = `capability.selectable is True`; framework/feature come from `capability.*`; ordering = topological over `depends_on`.
- **Key code fragments:**
```python
def _closure(selected, by_id):
    out, stack = set(selected), list(selected)
    while stack:
        for dep in by_id[stack.pop()].get("depends_on", []):
            if dep not in out: out.add(dep); stack.append(dep)
    return out
# topo sort the closure by depends_on -> ordered build_plan
```
- **Edge cases:** a `depends_on` id missing -> error (broken graph); a `(framework, feature)` tagged to >1 spec -> error (violates spec-per-feature); cycle -> error; selecting a feature auto-includes its foundation deps.

**Constraints (hard):** menu derived from specs (never a parallel hand list); deterministic order; pure parsing (no network); single package `src/agents/registry/`.

## 7. Validation, edge cases & versioning policy
Registry is re-derived on every run, so it never drifts from the specs. Adding a feature = add a spec with `capability` front-matter; it appears in the menu automatically. Changing the front-matter schema is breaking for the parser (bump + regenerate).

## 8. Error handling + ABC instrumentation
A resolution run (selection -> build plan) is an agent action: log it to ABC (audit) via the router. Parser/graph errors fail fast with the offending spec id.

## 9. Testing & acceptance
Given fixture specs with `capability` front-matter: `menu()` groups correctly; `resolve_selection(["ingestion.streaming"])` returns the streaming spec + its `depends_on` closure; `build_plan` is topologically ordered; a duplicate `(framework, feature)` raises; a missing dep raises. Plus front-matter `acceptance`.

## 10. Examples
```
menu() -> {
  "ingestion":     ["batch", "streaming", "scd2"],
  "harmonization": ["acord-mapping", "silver-gold"],
}
# user picks ingestion/streaming:
build_plan(["ingestion.streaming"]) ->
  [foundation.contracts, foundation.config-model, dataio.readers,
   dataio.load-strategy, ingestion.engine, ingestion.streaming]   # foundation-first, ordered
```

## 11. Regeneration contract
`scaffold-then-edit`. The registry **data** (the menu) is always derived from specs (fully-generated at runtime); the resolver **code** is generated once then maintained.

## 12. References
`specs/_templates/component-spec.md` (the `capability` front-matter) · `docs/ROADMAP.md` (Track A) · `skills/_shared/project-structure.md` · `orchestration.router` spec.
