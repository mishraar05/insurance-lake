# InsureLake Specifications

**Purpose:** Markdown-first, edition-neutral specifications that serve as the **portable IP** for the InsureLake P&C accelerator. These specs are fed to Genie Code to generate framework components.

## 🎯 Principles

1. **Portable IP** - Specs are the source of truth, not the generated code
2. **Portable** - no environment-specific limitations baked into specs
3. **Genie-ready** - Written for AI consumption (clear, complete, structured)
4. **Self-contained** - Each spec has all information needed to build its component

## 📂 Organization

Specs are organized by **Epic domain**, matching the backlog structure:

```
specs/
├── foundation/       # FND - Config model, ABC SDK, core setup
├── ingestion/        # ING - Batch/stream loading, Auto Loader, SCD
├── harmonization/    # HARM - Transforms, ACORD mapping, silver/gold
├── quality/          # DQ & REC - Data quality rules, reconciliation
├── masking/          # MASK - PII classification, masking techniques
├── agentic/          # AGENT - Profiling, metadata gen, code gen
├── observability/    # OBS - Logging, monitoring, alerting
├── finops/           # FINOPS - Cost tracking, estimation, dashboard
├── orchestration/    # DEVOPS - Workflows, dependencies, CI/CD
└── _templates/       # Spec templates for consistency
```

## 📋 Spec Anatomy

Each spec follows this structure:

### Header
- **ID**: Backlog task ID(s) (e.g., FND-001, ING-010)
- **Title**: Clear component name
- **Owner**: Who authored/maintains
- **Status**: Draft | Review | Approved | Implemented
- **Depends On**: Other specs required first

### Body
1. **Purpose** - What problem does this solve?
2. **Requirements** - Functional + non-functional requirements
3. **Architecture** - High-level design, components, data flow
4. **Data Model** - Tables, schemas, relationships (if applicable)
5. **Implementation Details** - Code patterns, algorithms, libraries
6. **Validation Rules** - Business logic, constraints
7. **Error Handling** - Failure modes, error messages
8. **Testing** - Acceptance criteria, test scenarios
9. **Examples** - Usage examples, sample inputs/outputs
10. **References** - Links to docs, ADRs, related specs

## 🚀 Workflow

### 1. Author Spec (Genie / workspace)
```
Write spec in markdown → Review → Approve → Commit
```

### 2. Generate Code (Genie Code)
```
Feed spec to Genie Code → Review generated code → Test → Deploy
```

### 3. Iterate
```
Update spec → Regenerate code → Test changes → Deploy
```

## 📝 Spec Status

### ✅ Complete
- foundation/config-model-spec.md (FND-001)
- foundation/control-tables-ddl-spec.md (FND-002)
- foundation/fnd-003-implementation-summary.md (FND-003)

### 🚧 In Progress
- foundation/abc-sdk-spec.md (FND-010+)

### 📋 Planned
- All other specs (see roadmap in PROJECT_CONTEXT.md)

## 🎨 Templates

Use templates in `_templates/` for consistency:

- **spec-template.md** - General spec structure
- **engine-spec-template.md** - For engine components (ingestion, harmonization, DQ, etc.)
- **pattern-spec-template.md** - For implementation patterns (SCD, streaming, etc.)

## 🔗 Related Files

- [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) - Project decisions & roadmap
- [skills/README.md](../skills/README.md) - Skills that consume these specs
- [AI_Ready_Backlog_Tasks*.xlsx](../) - Detailed backlog tracking

## 💡 Tips for Spec Authors

1. **Be specific** - Avoid ambiguity; Genie needs clear instructions
2. **Include examples** - Show sample inputs/outputs, SQL, schemas
3. **Document constraints** - List all validation rules, limits, edge cases
4. **Think portable** - Specs should work across environments
5. **Link dependencies** - Reference other specs/tables/functions clearly
6. **Test acceptance** - Write testable acceptance criteria

## 📞 Questions?

See PROJECT_CONTEXT.md or reach out to the project owner.
