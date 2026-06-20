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

### SOLID Principles Application (REQUIRED for all components)

Describe how this component follows SOLID principles:

**Single Responsibility Principle (SRP):**
- Each class/module has ONE reason to change
- Example: Separate reader, validator, transformer, writer (not one god class)

**Open/Closed Principle (OCP):**
- Open for extension (via inheritance/composition), closed for modification
- Example: Base strategy interface with concrete implementations (Append, SCD2, etc.)

**Liskov Substitution Principle (LSP):**
- Subclasses are substitutable for their base classes
- Example: Any `Reader` subclass works in place of `Reader` base

**Interface Segregation Principle (ISP):**
- Many client-specific interfaces > one fat interface
- Example: Separate `Reader`, `StreamingReader`, `Writer` (not one `DataSource` with all methods)

**Dependency Inversion Principle (DIP):**
- Depend on abstractions, not concretions
- Example: Accept `Reader` interface, not `CSVReader` concrete class

### Design Patterns (use where applicable)

**Recommended patterns for this component:**
- **Strategy Pattern**: For interchangeable algorithms (load strategies, transformation logic)
- **Factory Pattern**: For object creation based on type/format (reader factories, strategy factories)
- **Template Method**: For workflows with fixed structure and variable steps (engine processing)
- **Builder Pattern**: For complex object construction (config builders)
- **Dependency Injection**: For testability and flexibility (inject dependencies, not hard-code them)

**Pattern application:**