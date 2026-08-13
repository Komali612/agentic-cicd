# ci-authoring

The shared engine every CI pipeline-authoring agent is built on. A worker agent
supplies two stack-specific pieces — a `Discoverer` and a `WorkflowGenerator` —
and the `AuthoringEngine` runs the rest of the loop identically for every stack.

```
clone → discover → (existing & compliant? → NO_CHANGE)
                 → generate → validate  ─┐ up to 3 attempts
                        ▲                 │
                        └── feedback ─────┘
                 → deploy (open PR, never merge) → PR_OPENED
                 → 3 failures → EXCEPTION
```

## What lives here (shared, identical across stacks)

| Module | Responsibility |
|--------|----------------|
| `engine.py` | the deterministic Discover→Generate→Validate→Deploy loop; **enforces the 3-attempt retry bound and check-existing-then-repair in code** |
| `discovery.py` | `Discoverer` ABC — each stack implements repo inspection |
| `generation.py` | `WorkflowGenerator` ABC — deterministic template rendering |
| `validation.py` | offline structural validation (YAML parses, required steps present, trigger wired) — **never executes the pipeline** |
| `config.py` / `models.py` | per-app `StepConfig` (PRD CR-2) and the value objects |
| `vcs.py` | clone, existing-pipeline detection, and opening the PR |

## Design invariants (from the PRD)

- **Deterministic output** — generation is template-based; the same repo yields
  the same YAML every run.
- **Bounded retry (NFR-3)** — 3 Generate→Validate attempts, then the repo becomes
  an exception. Enforced in `engine.py`, never delegated to an LLM.
- **Check-existing-then-repair (CR-3)** — a compliant existing pipeline is left
  untouched (`NO_CHANGE`).
- **Human gate (NFR-2)** — the engine opens a PR and never merges it.

## Consumers

`netcore-ci-agent` and `netlegacy-ci-agent` each depend on this package and add
only their stack-specific `Discoverer` + `WorkflowGenerator`.
